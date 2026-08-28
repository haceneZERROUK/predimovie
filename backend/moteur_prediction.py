# Le modele et ses artefacts sont recharges automatiquement quand le
# fichier modele_champion.joblib change sur disque (cf _charger_modele_
# si_necessaire) - necessaire depuis que le reentrainement mensuel
# (backend/reentrainement.py) peut le remplacer sans redemarrer l'API.
# predict.py et predictions_admin.py (relance hebdomadaire) passent tous
# les deux par predire() pour ne pas dupliquer ce chargement.
from pathlib import Path

import joblib
import numpy as np
from prometheus_client import Counter

from backend.config import CHEMIN_ARTEFACTS, CHEMIN_MODELE
from ml.data import construire_features_pour_predire

_modele = None
_artefacts = None
_derniere_maj_modele = None

# compte chaque appel reel au modele, contrairement au nombre de requetes
# HTTP (http_requests_total) qui ne dit pas combien de films ont ete
# predits en une seule requete /predictions/relancer
predictions_modele_total = Counter(
    "predictions_modele_total",
    "Nombre de fois ou le modele de ML a ete invoque pour predire un film",
)


def _charger_modele_si_necessaire() -> None:
    """Charge le modele au premier appel, puis le recharge uniquement si
    modele_champion.joblib a change depuis le dernier chargement (date de
    modification du fichier). Le garde-fou de ml/train.py (doit_remplacer_
    champion) est ce qui garantit qu'un modele degrade n'arrive jamais
    jusqu'ici - ce n'est plus un redemarrage manquant qui protege la prod."""
    global _modele, _artefacts, _derniere_maj_modele
    maj = Path(CHEMIN_MODELE).stat().st_mtime
    if _modele is None or maj != _derniere_maj_modele:
        _modele = joblib.load(CHEMIN_MODELE)
        _artefacts = joblib.load(CHEMIN_ARTEFACTS)
        _derniere_maj_modele = maj


def predire(id_oeuvre: int) -> int:
    """Renvoie le nombre d'entrees premiere semaine predit pour ce film.
    Leve ValueError si le film n'existe pas (remonte depuis construire_
    features_pour_predire)."""
    _charger_modele_si_necessaire()
    X = construire_features_pour_predire(id_oeuvre, _artefacts)
    prediction_log = _modele.predict(X)
    predictions_modele_total.inc()
    return int(np.expm1(prediction_log[0]).clip(min=0))
