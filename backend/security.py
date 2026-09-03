# Hachage des mots de passe (bcrypt) et gestion des tokens JWT
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from backend.config import JWT_ALGORITHME, JWT_DUREE_VALIDITE_MINUTES, JWT_SECRET_KEY


def hacher_mot_de_passe(mot_de_passe: str) -> str:
    """Hache le mot de passe avec bcrypt, qui gere le sel tout seul."""
    sel = bcrypt.gensalt()
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel).decode("utf-8")


def verifier_mot_de_passe(mot_de_passe: str, hash_stocke: str) -> bool:
    """Compare le mot de passe saisi au hash stocke en base."""
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke.encode("utf-8"))


def creer_token(mail: str, role: str) -> str:
    """Cree un token JWT avec le mail et le role dedans, valable
    JWT_DUREE_VALIDITE_MINUTES minutes."""
    expiration = datetime.now(UTC) + timedelta(minutes=JWT_DUREE_VALIDITE_MINUTES)
    payload = {"sub": mail, "role": role, "exp": expiration}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHME)


def decoder_token(token: str) -> dict:
    """Verifie la signature et l'expiration du token et renvoie son
    contenu. Leve jwt.InvalidTokenError si ca ne passe pas."""
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHME])
