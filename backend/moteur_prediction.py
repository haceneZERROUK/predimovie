# Le modele et ses artefacts sont charges ici une seule fois, au demarrage
# de l'API. predict.py et predictions_admin.py (relance hebdomadaire)
# passent tous les deux par predire() pour ne pas dupliquer ce chargement.
import joblib
import numpy as np
from prometheus_client import Counter

from backend.config import CHEMIN_ARTEFACTS, CHEMIN_MODELE
from ml.data import construire_features_pour_predire

_modele = joblib.load(CHEMIN_MODELE)
_artefacts = joblib.load(CHEMIN_ARTEFACTS)

# compte chaque appel reel au modele, contrairement au nombre de requetes
# HTTP (http_requests_total) qui ne dit pas combien de films ont ete
# predits en une seule requete /predictions/relancer
predictions_modele_total = Counter(
    "predictions_modele_total",
    "Nombre de fois ou le modele de ML a ete invoque pour predire un film",
)


def predire(id_oeuvre: int) -> int:
    """Renvoie le nombre d'entrees premiere semaine predit pour ce film.
    Leve ValueError si le film n'existe pas (remonte depuis construire_
    features_pour_predire)."""
    X = construire_features_pour_predire(id_oeuvre, _artefacts)
    prediction_log = _modele.predict(X)
    predictions_modele_total.inc()
    return int(np.expm1(prediction_log[0]).clip(min=0))
