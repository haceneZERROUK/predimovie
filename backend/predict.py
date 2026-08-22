# Route de prediction : utilise le modele deja charge dans
# moteur_prediction.py pour predire les entrees d'un film deja en base
# (typiquement un film pas encore sorti, scrape par le flux A).
from fastapi import APIRouter, Depends, HTTPException

from backend.auth import utilisateur_connecte
from backend.moteur_prediction import predire
from backend.schemas import PredictionDemande, PredictionReponse
from database.base import SessionLocal
from database.models import Oeuvre

router = APIRouter()


@router.post("/predict", response_model=PredictionReponse)
def predict(demande: PredictionDemande, _utilisateur: dict = Depends(utilisateur_connecte)):
    session = SessionLocal()
    try:
        oeuvre = session.get(Oeuvre, demande.id_oeuvre)
        if oeuvre is None:
            raise HTTPException(status_code=404, detail="Film introuvable")
    finally:
        session.close()

    try:
        prediction = predire(demande.id_oeuvre)
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur

    return PredictionReponse(
        id_oeuvre=oeuvre.id_oeuvre,
        nom_francais=oeuvre.nom_francais,
        entrees_premiere_semaine_predites=prediction,
    )
