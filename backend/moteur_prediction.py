# Chargement du modele et prediction. Le modele est recharge tout seul
# quand le fichier .joblib change, comme ca le reentrainement mensuel n'a
# pas besoin de redemarrer l'API.
from pathlib import Path

import joblib
import numpy as np
from prometheus_client import Counter

from backend.config import CHEMIN_ARTEFACTS, CHEMIN_MODELE
from ml.data import construire_features_pour_predire

_modele = None
_artefacts = None
_derniere_maj_modele = None

# compte les appels au modele, et pas les requetes HTTP : une seule
# requete /predictions/relancer peut predire des dizaines de films
predictions_modele_total = Counter(
    "predictions_modele_total",
    "Nombre de fois ou le modele de ML a ete invoque pour predire un film",
)


def _charger_modele_si_necessaire() -> None:
    """Charge le modele au premier appel, puis seulement si le fichier a
    change depuis (on regarde sa date de modification)."""
    global _modele, _artefacts, _derniere_maj_modele
    maj = Path(CHEMIN_MODELE).stat().st_mtime
    if _modele is None or maj != _derniere_maj_modele:
        _modele = joblib.load(CHEMIN_MODELE)
        _artefacts = joblib.load(CHEMIN_ARTEFACTS)
        _derniere_maj_modele = maj


def predire(id_oeuvre: int) -> int:
    """Renvoie les entrees de 1ere semaine predites pour ce film.
    Leve ValueError si le film n'existe pas."""
    _charger_modele_si_necessaire()
    X = construire_features_pour_predire(id_oeuvre, _artefacts)
    prediction_log = _modele.predict(X)
    predictions_modele_total.inc()
    return int(np.expm1(prediction_log[0]).clip(min=0))
