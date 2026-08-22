# Routes reservees a l'admin : relancer les predictions sur les films
# pas encore sortis (et les stocker), et voir l'historique predit/reel
# une fois que ces films sont sortis pour de vrai.
from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from backend.auth import utilisateur_admin
from backend.moteur_prediction import predire
from backend.schemas import HistoriquePrediction, RelanceReponse
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


@router.get("/predictions/historique", response_model=list[HistoriquePrediction])
def historique_predictions(_utilisateur: dict = Depends(utilisateur_admin)):
    """Compare chaque prediction stockee au resultat reel, pour les films
    qui sont maintenant sortis (entrees_premiere_semaine connu)."""
    session = SessionLocal()
    try:
        lignes = (
            session.query(Prediction, Oeuvre.entrees_premiere_semaine)
            .join(Oeuvre, Oeuvre.id_oeuvre == Prediction.id_oeuvre)
            .filter(Oeuvre.entrees_premiere_semaine.isnot(None))
            .order_by(Prediction.date_prediction.desc())
            .all()
        )
        return [
            HistoriquePrediction(
                nom_francais=prediction.nom_francais,
                entrees_premiere_semaine_predites=prediction.entrees_premiere_semaine_predites,
                entrees_premiere_semaine_reelles=reel,
                date_prediction=prediction.date_prediction,
                ecart=prediction.entrees_premiere_semaine_predites - reel,
            )
            for prediction, reel in lignes
        ]
    finally:
        session.close()
