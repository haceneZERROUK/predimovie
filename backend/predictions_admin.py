# Routes admin : relancer les predictions sur les films pas encore sortis,
# et consulter l'historique predit/reel une fois qu'ils sont sortis.
from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException

from backend.auth import utilisateur_admin
from backend.config import PREDICTION_API_KEY
from backend.moteur_prediction import predire
from backend.schemas import HistoriquePrediction, HistoriqueReponse, RelanceReponse
from backend.security import cle_api_valide
from database.base import SessionLocal
from database.models import Oeuvre, Prediction

router = APIRouter()


def verifier_cle_api(x_api_key: str = Header(default="")):
    if not cle_api_valide(x_api_key, PREDICTION_API_KEY):
        raise HTTPException(status_code=401, detail="Clé API invalide")


def _relancer_predictions() -> int:
    session = SessionLocal()
    try:
        films = session.query(Oeuvre).filter(Oeuvre.entrees_premiere_semaine.is_(None)).all()
        maintenant = datetime.now(UTC)
        nombre = 0
        for film in films:
            try:
                valeur_predite = predire(film.id_oeuvre)
            except ValueError:
                # film trop mal renseigne, on le saute au lieu de faire
                # planter toute la relance
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
        return nombre
    finally:
        session.close()


@router.post("/predictions/relancer", response_model=RelanceReponse)
def relancer_predictions(_utilisateur: dict = Depends(utilisateur_admin)):
    return RelanceReponse(nombre_predictions=_relancer_predictions())


@router.post(
    "/admin/predictions/relancer",
    response_model=RelanceReponse,
    dependencies=[Depends(verifier_cle_api)],
)
def relancer_predictions_auto():
    """Meme chose que /predictions/relancer, mais avec une cle API au lieu
    d'un JWT admin. C'est ce qu'appelle le cron hebdo."""
    return RelanceReponse(nombre_predictions=_relancer_predictions())


@router.get("/predictions/historique", response_model=HistoriqueReponse)
def historique_predictions(
    semaine: date | None = None, _utilisateur: dict = Depends(utilisateur_admin)
):
    """Classement des films sortis par entrees reelles, avec la prediction
    a cote quand il y en a une. Sans parametre on renvoie les 4 dernieres
    semaines, avec `semaine` (le mercredi de sortie) juste celle-la."""
    session = SessionLocal()
    try:
        # outerjoin depuis Oeuvre : les films sans prediction stockee
        # doivent quand meme apparaitre
        requete = (
            session.query(Oeuvre, Prediction)
            .outerjoin(Prediction, Prediction.id_oeuvre == Oeuvre.id_oeuvre)
            .filter(Oeuvre.entrees_premiere_semaine.isnot(None))
        )
        if semaine is not None:
            requete = requete.filter(Oeuvre.date_sortie == semaine)
        else:
            requete = requete.filter(Oeuvre.date_sortie >= date.today() - timedelta(weeks=4))

        # un film peut avoir plusieurs predictions si on a relance
        # plusieurs fois : on trie par date pour garder la plus recente
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
