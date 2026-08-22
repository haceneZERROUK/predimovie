# Route de prediction : charge le modele champion une seule fois (pas a
# chaque requete), et l'utilise pour predire les entrees d'un film deja
# en base (typiquement un film pas encore sorti, scrape par le flux A).
import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException

from backend.auth import utilisateur_connecte
from backend.config import CHEMIN_ARTEFACTS, CHEMIN_MODELE
from backend.schemas import PredictionDemande, PredictionReponse
from database.base import SessionLocal
from database.models import Oeuvre
from ml.data import construire_features_pour_predire

router = APIRouter()

# charges une seule fois au demarrage de l'API, pas a chaque appel
_modele = joblib.load(CHEMIN_MODELE)
_artefacts = joblib.load(CHEMIN_ARTEFACTS)


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
        X = construire_features_pour_predire(demande.id_oeuvre, _artefacts)
    except ValueError as erreur:
        raise HTTPException(status_code=404, detail=str(erreur)) from erreur

    prediction_log = _modele.predict(X)
    prediction = int(np.expm1(prediction_log[0]).clip(min=0))

    return PredictionReponse(
        id_oeuvre=oeuvre.id_oeuvre,
        nom_francais=oeuvre.nom_francais,
        entrees_premiere_semaine_predites=prediction,
    )
