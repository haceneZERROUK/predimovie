# Config du backend : juste des variables d'environnement, comme dans
# data_engineering/config.py.
import os

# secret qui sert a signer les tokens JWT. En dev on a une valeur par
# defaut pour que ca marche out-of-the-box, mais en prod il faut
# absolument la changer via la variable d'environnement.
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-moi-en-prod-je-suis-juste-un-defaut-dev")
JWT_ALGORITHME = "HS256"
JWT_DUREE_VALIDITE_MINUTES = 60

CHEMIN_MODELE = os.environ.get("CHEMIN_MODELE", "ml/modele_champion.joblib")
CHEMIN_ARTEFACTS = os.environ.get("CHEMIN_ARTEFACTS", "ml/artefacts_features.joblib")

# cle partagee avec N8n pour declencher /admin/reentrainer-modele chaque
# mois - meme principe que SCRAPER_API_KEY dans data_engineering/config.py
TRAIN_API_KEY = os.environ.get("TRAIN_API_KEY", "")

# cle partagee avec N8n pour declencher /admin/predictions/relancer chaque
# semaine (meme principe, cle dediee pour ne pas reutiliser TRAIN_API_KEY)
PREDICTION_API_KEY = os.environ.get("PREDICTION_API_KEY", "")
