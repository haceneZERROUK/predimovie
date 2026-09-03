# Config du backend, lue dans les variables d'environnement
import os

# secret pour signer les tokens JWT. La valeur par defaut sert juste en
# dev, en prod il faut la changer.
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "change-moi-en-prod-je-suis-juste-un-defaut-dev")
JWT_ALGORITHME = "HS256"
JWT_DUREE_VALIDITE_MINUTES = 60

CHEMIN_MODELE = os.environ.get("CHEMIN_MODELE", "ml/modele_champion.joblib")
CHEMIN_ARTEFACTS = os.environ.get("CHEMIN_ARTEFACTS", "ml/artefacts_features.joblib")

# cle utilisee par le cron mensuel pour appeler /admin/reentrainer-modele
TRAIN_API_KEY = os.environ.get("TRAIN_API_KEY", "")

# cle du cron hebdo pour /admin/predictions/relancer. Une cle a part pour
# ne pas melanger avec celle du reentrainement.
PREDICTION_API_KEY = os.environ.get("PREDICTION_API_KEY", "")
