# Tests du hachage des mots de passe et des tokens JWT. Ni postgres ni
# FastAPI la-dedans.
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from backend.config import JWT_ALGORITHME, JWT_SECRET_KEY
from backend.security import creer_token, decoder_token, hacher_mot_de_passe, verifier_mot_de_passe


def test_hacher_puis_verifier_mot_de_passe_correct():
    hash_stocke = hacher_mot_de_passe("motdepasse123")
    assert verifier_mot_de_passe("motdepasse123", hash_stocke) is True


def test_verifier_refuse_mauvais_mot_de_passe():
    hash_stocke = hacher_mot_de_passe("motdepasse123")
    assert verifier_mot_de_passe("autrechose", hash_stocke) is False


def test_hacher_ne_stocke_jamais_le_mot_de_passe_en_clair():
    hash_stocke = hacher_mot_de_passe("motdepasse123")
    assert "motdepasse123" not in hash_stocke


def test_creer_puis_decoder_token_valide():
    token = creer_token(mail="cinema@example.com", role="cinema")
    contenu = decoder_token(token)
    assert contenu["sub"] == "cinema@example.com"
    assert contenu["role"] == "cinema"


def test_decoder_token_invalide_leve_une_erreur():
    with pytest.raises(jwt.InvalidTokenError):
        decoder_token("ceci-nest-pas-un-token")


def test_decoder_token_expire_leve_une_erreur():
    # on fabrique un token deja expire pour verifier que c'est bien
    # controle au decodage
    payload = {
        "sub": "cinema@example.com",
        "role": "cinema",
        "exp": datetime.now(UTC) - timedelta(seconds=1),
    }
    token_expire = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHME)

    with pytest.raises(jwt.ExpiredSignatureError):
        decoder_token(token_expire)
