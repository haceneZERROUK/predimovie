# Route de reentrainement du modele, appelee par le cron mensuel. Cle API
# dans un header plutot qu'un JWT, vu que c'est un script qui appelle.
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException

from backend.config import TRAIN_API_KEY
from backend.security import cle_api_valide
from ml.train import main as reentrainer_le_modele

router = APIRouter()
logger = logging.getLogger(__name__)


def verifier_cle_api(x_api_key: str = Header(default="")):
    if not cle_api_valide(x_api_key, TRAIN_API_KEY):
        raise HTTPException(status_code=401, detail="Clé API invalide")


def _reentrainer_en_arriere_plan() -> None:
    try:
        reentrainer_le_modele()
    except Exception:
        # on est en tache de fond, il n'y a plus de requete a qui renvoyer
        # l'erreur, donc on la logue
        logger.exception("Echec du reentrainement mensuel du modele")


@router.post("/admin/reentrainer-modele", dependencies=[Depends(verifier_cle_api)])
def reentrainer_modele(taches_de_fond: BackgroundTasks):
    """Lance ml/train.py en arriere-plan et repond tout de suite :
    l'entrainement prend plusieurs dizaines de minutes."""
    taches_de_fond.add_task(_reentrainer_en_arriere_plan)
    return {"statut": "reentrainement lance en arriere-plan"}
