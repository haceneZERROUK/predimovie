# Test d'integration de /auth/login : cree un vrai compte en base de
# test, verifie que la connexion marche, puis nettoie derriere lui.
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import hacher_mot_de_passe
from database.base import SessionLocal
from database.models import Compte, RoleCompte

client = TestClient(app)


@pytest.fixture
def compte_test():
    """Cree un compte reel (commit) car /auth/login ouvre sa propre
    session vers la vraie base, independante des fixtures habituelles
    a rollback. On le supprime nous-memes a la fin du test."""
    session = SessionLocal()
    compte = Compte(
        mail="test-backend@example.com",
        mot_de_passe=hacher_mot_de_passe("motdepasse123"),
        role=RoleCompte.CINEMA,
        nom_cinema="Cinema de test",
        date_inscription=date.today(),
        statut_compte=True,
    )
    session.add(compte)
    session.commit()
    session.refresh(compte)
    yield compte
    session.delete(compte)
    session.commit()
    session.close()


def test_health():
    reponse = client.get("/health")
    assert reponse.status_code == 200


def test_login_avec_bons_identifiants(compte_test):
    reponse = client.post(
        "/auth/login", json={"mail": "test-backend@example.com", "mot_de_passe": "motdepasse123"}
    )
    assert reponse.status_code == 200
    assert "access_token" in reponse.json()


def test_login_avec_mauvais_mot_de_passe(compte_test):
    reponse = client.post(
        "/auth/login", json={"mail": "test-backend@example.com", "mot_de_passe": "faux"}
    )
    assert reponse.status_code == 401


def test_login_avec_mail_inconnu():
    reponse = client.post(
        "/auth/login", json={"mail": "inconnu@example.com", "mot_de_passe": "peu importe"}
    )
    assert reponse.status_code == 401
