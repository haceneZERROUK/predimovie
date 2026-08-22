# Le modele et ses artefacts sont charges ici une seule fois, au demarrage
# de l'API. predict.py et predictions_admin.py (relance hebdomadaire)
# passent tous les deux par predire() pour ne pas dupliquer ce chargement.
import joblib
import numpy as np

from backend.config import CHEMIN_ARTEFACTS, CHEMIN_MODELE
from ml.data import construire_features_pour_predire

_modele = joblib.load(CHEMIN_MODELE)
_artefacts = joblib.load(CHEMIN_ARTEFACTS)


def predire(id_oeuvre: int) -> int:
    """Renvoie le nombre d'entrees premiere semaine predit pour ce film.
    Leve ValueError si le film n'existe pas (remonte depuis construire_
    features_pour_predire)."""
    X = construire_features_pour_predire(id_oeuvre, _artefacts)
    prediction_log = _modele.predict(X)
    return int(np.expm1(prediction_log[0]).clip(min=0))
