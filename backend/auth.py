# Connexion : verifie le mail et le mot de passe dans la table compte,
# et renvoie un token JWT.
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func

from backend.schemas import ConnexionDemande, ConnexionReponse
from backend.security import creer_token, decoder_token, verifier_mot_de_passe
from database.base import SessionLocal
from database.models import Compte

router = APIRouter()
schema_bearer = HTTPBearer()


@router.post("/auth/login", response_model=ConnexionReponse)
def login(demande: ConnexionDemande):
    session = SessionLocal()
    try:
        # on compare sans tenir compte de la casse ni des espaces autour :
        # quelqu'un qui tape Cine@Test.fr doit pouvoir se connecter. On passe
        # par func.lower cote SQL plutot que de juste minusculer la saisie,
        # comme ca les comptes deja enregistres avec une majuscule marchent
        # aussi, sans avoir a nettoyer la base.
        mail = demande.mail.strip().lower()
        compte = session.query(Compte).filter(func.lower(Compte.mail) == mail).first()

        # meme message que le compte existe ou pas, pour ne pas aider
        # quelqu'un qui cherche des mails valides
        erreur_generique = HTTPException(status_code=401, detail="Identifiants invalides")

        if compte is None or not compte.statut_compte:
            raise erreur_generique
        if not verifier_mot_de_passe(demande.mot_de_passe, compte.mot_de_passe):
            raise erreur_generique

        compte.derniere_connexion = datetime.now(UTC)
        session.commit()

        token = creer_token(mail=compte.mail, role=compte.role.value)
        return ConnexionReponse(access_token=token)
    finally:
        session.close()


def utilisateur_connecte(
    identifiants: HTTPAuthorizationCredentials = Depends(schema_bearer),
) -> dict:
    """Dependance des routes protegees : verifie le token JWT du header
    Authorization et renvoie son contenu, ou renvoie une 401."""
    try:
        return decoder_token(identifiants.credentials)
    except Exception as erreur:
        raise HTTPException(status_code=401, detail="Token invalide ou expire") from erreur


def utilisateur_admin(utilisateur: dict = Depends(utilisateur_connecte)) -> dict:
    """Pareil que utilisateur_connecte mais verifie en plus que le role
    est admin."""
    if utilisateur.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Reserve aux administrateurs")
    return utilisateur
