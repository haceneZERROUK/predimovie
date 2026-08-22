# Route de connexion : verifie mail + mot de passe contre la table
# compte, et renvoie un token JWT si c'est bon.
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

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
        compte = session.query(Compte).filter_by(mail=demande.mail).first()

        # meme message d'erreur que le compte existe ou pas / le mot de
        # passe soit faux : pas d'indice a donner a quelqu'un qui essaie
        # de deviner des mails valides
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
    """A mettre en dependance sur les routes protegees : verifie le token
    JWT envoye dans le header Authorization, renvoie son contenu (mail,
    role) ou refuse l'acces (401)."""
    try:
        return decoder_token(identifiants.credentials)
    except Exception as erreur:
        raise HTTPException(status_code=401, detail="Token invalide ou expire") from erreur


def utilisateur_admin(utilisateur: dict = Depends(utilisateur_connecte)) -> dict:
    """Meme chose que utilisateur_connecte, mais en plus verifie que le
    role est admin. A utiliser sur les routes reservees a l'admin
    (relancer les predictions, voir l'historique...)."""
    if utilisateur.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Reserve aux administrateurs")
    return utilisateur
