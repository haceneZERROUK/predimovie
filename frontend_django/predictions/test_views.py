# Tests des vues de connexion/deconnexion. On ne tape jamais le vrai
# backend FastAPI ici : on remplace appel_login par une fausse fonction
# (monkeypatch) pour rester rapide et independant du reseau.
import jwt
import pytest
from django.urls import reverse

from predictions.api_client import ErreurAPI

FAUX_TOKEN = jwt.encode(
    {"sub": "cinema@example.com", "role": "cinema"},
    "peu-importe-cle-de-test-bidon",
    algorithm="HS256",
)


@pytest.mark.django_db
def test_login_get_affiche_le_formulaire(client):
    reponse = client.get(reverse("predictions:login"))
    assert reponse.status_code == 200
    assert b"mail" in reponse.content


@pytest.mark.django_db
def test_login_reussi_met_le_token_en_session(client, monkeypatch):
    monkeypatch.setattr(
        "predictions.views.appel_login",
        lambda mail, mot_de_passe: {"access_token": FAUX_TOKEN, "token_type": "bearer"},
    )
    reponse = client.post(
        reverse("predictions:login"),
        {"mail": "cinema@example.com", "mot_de_passe": "bonmotdepasse"},
    )
    assert reponse.status_code == 302
    assert client.session["token"] == FAUX_TOKEN
    assert client.session["role"] == "cinema"


@pytest.mark.django_db
def test_login_rate_naffiche_pas_de_session(client, monkeypatch):
    def faux_login_qui_echoue(mail, mot_de_passe):
        raise ErreurAPI("Identifiants invalides")

    monkeypatch.setattr("predictions.views.appel_login", faux_login_qui_echoue)
    reponse = client.post(
        reverse("predictions:login"),
        {"mail": "cinema@example.com", "mot_de_passe": "mauvais"},
    )
    assert reponse.status_code == 200
    assert "token" not in client.session
    assert b"Identifiants invalides" in reponse.content


@pytest.mark.django_db
def test_accueil_redirige_vers_login_si_pas_connecte(client):
    reponse = client.get(reverse("predictions:accueil"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:login")


@pytest.mark.django_db
def test_accueil_accessible_si_connecte(client):
    session = client.session
    session["token"] = FAUX_TOKEN
    session["mail"] = "cinema@example.com"
    session["role"] = "cinema"
    session.save()

    reponse = client.get(reverse("predictions:accueil"))
    assert reponse.status_code == 200


@pytest.mark.django_db
def test_logout_vide_la_session(client):
    session = client.session
    session["token"] = FAUX_TOKEN
    session.save()

    reponse = client.get(reverse("predictions:logout"))
    assert reponse.status_code == 302
    assert "token" not in client.session
