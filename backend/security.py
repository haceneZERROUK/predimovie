# Hachage de mot de passe (bcrypt) et creation/verification de token JWT.
# Rien de specifique a FastAPI ici, facile a tester tout seul.
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from backend.config import JWT_ALGORITHME, JWT_DUREE_VALIDITE_MINUTES, JWT_SECRET_KEY


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Transforme un mot de passe en clair en hash bcrypt, a stocker en
    base. bcrypt gere le "sel" tout seul, pas besoin d'y penser."""
    sel = bcrypt.gensalt()
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """Compare un mot de passe en clair (saisi par l'utilisateur) au hash
    stocke en base. Ne jamais comparer deux mots de passe en clair !"""
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))


def creer_token(mail: str, role: str) -> str:
    """Cree un token JWT qui prouve que l'utilisateur mail/role s'est
    bien connecte, valable JWT_DUREE_VALIDITE_MINUTES minutes."""
    expiration = datetime.now(UTC) + timedelta(minutes=JWT_DUREE_VALIDITE_MINUTES)
    payload = {"sub": mail, "role": role, "exp": expiration}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHME)


def decoder_token(token: str) -> dict:
    """Verifie la signature et l'expiration d'un token, renvoie son
    contenu. Leve jwt.InvalidTokenError si le token est invalide/expire."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHME])
