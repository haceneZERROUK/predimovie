# Tests des routes admin de gestion des comptes cinema : lister et
# creer. Un compte cinema ne doit pas pouvoir y acceder (403).
from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import creer_token, hacher_mot_de_passe
from database.base import SessionLocal
from database.models import Compte, RoleCompte

client = TestClient(app)


def _token(role):
    return creer_token(mail="test@example.com", role=role)


@pytest.fixture
def compte_cinema_test():
    session = SessionLocal()
    compte = Compte(
        mail="cinema-test-comptes@example.com",
        mot_de_passe=hacher_mot_de_passe("peu-importe"),
        role=RoleCompte.CINEMA,
        nom_cinema="Cinema Test Comptes",
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


def test_lister_comptes_refuse_un_compte_cinema():
    reponse = client.get("/comptes", headers={"Authorization": f"Bearer {_token('cinema')}"})
    assert reponse.status_code == 403


def test_lister_comptes_contient_le_compte_cinema(compte_cinema_test):
    reponse = client.get("/comptes", headers={"Authorization": f"Bearer {_token('admin')}"})
    assert reponse.status_code == 200
    mails = [c["mail"] for c in reponse.json()]
    assert compte_cinema_test.mail in mails


def test_creer_compte_refuse_un_compte_cinema():
    reponse = client.post(
        "/comptes",
        json={"mail": "nouveau@example.com", "mot_de_passe": "azerty123", "nom_cinema": "Nouveau"},
        headers={"Authorization": f"Bearer {_token('cinema')}"},
    )
    assert reponse.status_code == 403


def test_creer_compte_cree_un_compte_cinema():
    reponse = client.post(
        "/comptes",
        json={
            "mail": "nouveau-cinema@example.com",
            "mot_de_passe": "azerty123",
            "nom_cinema": "Cinema Le Nouveau",
        },
        headers={"Authorization": f"Bearer {_token('admin')}"},
    )
    assert reponse.status_code == 201
    corps = reponse.json()
    assert corps["mail"] == "nouveau-cinema@example.com"
    assert corps["nom_cinema"] == "Cinema Le Nouveau"
    assert "mot_de_passe" not in corps

    session = SessionLocal()
    compte = session.query(Compte).filter_by(mail="nouveau-cinema@example.com").first()
    assert compte is not None
    assert compte.role == RoleCompte.CINEMA
    session.delete(compte)
    session.commit()
    session.close()


def test_creer_compte_refuse_un_mail_deja_pris(compte_cinema_test):
    reponse = client.post(
        "/comptes",
        json={
            "mail": compte_cinema_test.mail,
            "mot_de_passe": "azerty123",
            "nom_cinema": "Doublon",
        },
        headers={"Authorization": f"Bearer {_token('admin')}"},
    )
    assert reponse.status_code == 409


def test_supprimer_compte_refuse_un_compte_cinema(compte_cinema_test):
    reponse = client.delete(
        f"/comptes/{compte_cinema_test.id_compte}",
        headers={"Authorization": f"Bearer {_token('cinema')}"},
    )
    assert reponse.status_code == 403


def test_supprimer_compte_supprime_bien_le_compte(compte_cinema_test):
    id_compte = compte_cinema_test.id_compte
    reponse = client.delete(
        f"/comptes/{id_compte}", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 204

    session = SessionLocal()
    assert session.query(Compte).filter_by(id_compte=id_compte).first() is None
    session.close()


def test_supprimer_compte_404_si_inconnu():
    reponse = client.delete(
        "/comptes/999999", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 404


def test_supprimer_compte_refuse_un_compte_admin():
    """La suppression est volontairement limitee aux comptes CINEMA :
    on ne peut pas supprimer un compte admin par cette route."""
    session = SessionLocal()
    admin = Compte(
        mail="autre-admin@example.com",
        mot_de_passe=hacher_mot_de_passe("peu-importe"),
        role=RoleCompte.ADMIN,
        date_inscription=date.today(),
        statut_compte=True,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    id_admin = admin.id_compte

    reponse = client.delete(
        f"/comptes/{id_admin}", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 404

    session.delete(admin)
    session.commit()
    session.close()
