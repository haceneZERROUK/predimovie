# Route de reentrainement mensuel du modele, declenchee par N8n (cron).
# Meme pattern que data_engineering/main.py : cle API partagee dans un
# header, pas de JWT - c'est une machine qui appelle, pas un utilisateur.
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from backend.config import TRAIN_API_KEY
from ml.train import main as reentrainer_le_modele

router = APIRouter()
logger = logging.getLogger(__name__)


def verifier_cle_api(x_api_key: str = Header(default="")):
    if x_api_key != TRAIN_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


def _reentrainer_en_arriere_plan() -> None:
    try:
        reentrainer_le_modele()
    except Exception:
        # tache de fond sans requete HTTP a qui repondre en cas d'echec :
        # on logue, a defaut d'une vraie alerte (piste, pas fait ici)
        logger.exception("Echec du reentrainement mensuel du modele")


@router.post("/admin/reentrainer-modele", dependencies=[Depends(verifier_cle_api)])
def reentrainer_modele(taches_de_fond: BackgroundTasks):
    """Relance ml/train.py en arriere-plan : la recherche d'hyperparametres
    prend plusieurs dizaines de minutes, hors de question de faire attendre
    la reponse HTTP (le node N8n timeoutrait bien avant). Le nouveau modele
    ne remplace modele_champion.joblib que si le garde-fou (doit_remplacer_
    champion, cf ml/train.py) accepte sa degradation de RMSE."""
    taches_de_fond.add_task(_reentrainer_en_arriere_plan)
    return {"statut": "reentrainement lance en arriere-plan"}
