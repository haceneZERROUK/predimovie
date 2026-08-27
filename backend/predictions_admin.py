# Routes reservees a l'admin : relancer les predictions sur les films
# pas encore sortis (et les stocker), et voir l'historique predit/reel
# une fois que ces films sont sortis pour de vrai.
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends

from backend.auth import utilisateur_admin
from backend.moteur_prediction import predire
from backend.schemas import HistoriquePrediction, HistoriqueReponse, RelanceReponse
from database.base import SessionLocal
from database.models import Oeuvre, Prediction

router = APIRouter()


@router.post("/predictions/relancer", response_model=RelanceReponse)
def relancer_predictions(_utilisateur: dict = Depends(utilisateur_admin)):
    session = SessionLocal()
    try:
        films = session.query(Oeuvre).filter(Oeuvre.entrees_premiere_semaine.is_(None)).all()
        maintenant = datetime.now(UTC)
        nombre = 0
        for film in films:
            try:
                valeur_predite = predire(film.id_oeuvre)
            except ValueError:
                # film mal renseigne (pas assez d'infos pour les features),
                # on le saute plutot que de faire planter toute la relance
                continue
            session.add(
                Prediction(
                    id_oeuvre=film.id_oeuvre,
                    nom_francais=film.nom_francais,
                    entrees_premiere_semaine_predites=valeur_predite,
                    date_prediction=maintenant,
                )
            )
            nombre += 1
        session.commit()
        return RelanceReponse(nombre_predictions=nombre)
    finally:
        session.close()


@router.get("/predictions/historique", response_model=HistoriqueReponse)
def historique_predictions(
    semaine: date | None = None, _utilisateur: dict = Depends(utilisateur_admin)
):
    """Top des films sortis (classes par vraies entrees, decroissant), pour
    les films qui sont maintenant sortis (entrees_premiere_semaine connu).
    La prediction stockee est affichee quand elle existe (certains films
    n'en ont jamais eu, personne n'a clique "Relancer" avant leur sortie).

    Sans le parametre `semaine`, affiche les 4 dernieres semaines de
    sorties. Avec `semaine` (date du mercredi de sortie), affiche
    uniquement cette semaine-la - c'est ce qu'utilise le menu deroulant
    du front pour remonter plus loin dans l'historique."""
    session = SessionLocal()
    try:
        # LEFT JOIN a partir de Oeuvre (pas Prediction) : un film sorti sans
        # prediction stockee doit quand meme apparaitre dans le classement
        requete = (
            session.query(Oeuvre, Prediction)
            .outerjoin(Prediction, Prediction.id_oeuvre == Oeuvre.id_oeuvre)
            .filter(Oeuvre.entrees_premiere_semaine.isnot(None))
        )
        if semaine is not None:
            requete = requete.filter(Oeuvre.date_sortie == semaine)
        else:
            requete = requete.filter(Oeuvre.date_sortie >= date.today() - timedelta(weeks=4))

        # un film relance plusieurs fois (bouton "Relancer les predictions"
        # clique a plusieurs reprises) a plusieurs lignes de prediction :
        # on trie par date de prediction pour ne garder que la plus recente
        lignes = requete.order_by(
            Oeuvre.entrees_premiere_semaine.desc(), Prediction.date_prediction.desc()
        ).all()
        deja_vus = set()
        predictions = []
        for oeuvre, prediction in lignes:
            if oeuvre.id_oeuvre in deja_vus:
                continue
            deja_vus.add(oeuvre.id_oeuvre)
            reel = oeuvre.entrees_premiere_semaine
            predite = prediction.entrees_premiere_semaine_predites if prediction else None
            predictions.append(
                HistoriquePrediction(
                    nom_francais=oeuvre.nom_francais,
                    entrees_premiere_semaine_predites=predite,
                    entrees_premiere_semaine_reelles=reel,
                    date_prediction=prediction.date_prediction if prediction else None,
                    ecart=(predite - reel) if predite is not None else None,
                )
            )

        semaines_disponibles = (
            session.query(Oeuvre.date_sortie)
            .filter(
                Oeuvre.entrees_premiere_semaine.isnot(None),
                Oeuvre.date_sortie.isnot(None),
            )
            .distinct()
            .order_by(Oeuvre.date_sortie.desc())
            .all()
        )

        return HistoriqueReponse(
            predictions=predictions,
            semaines_disponibles=[s[0] for s in semaines_disponibles],
        )
    finally:
        session.close()
