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
FAUX_TOKEN_ADMIN = jwt.encode(
    {"sub": "admin@example.com", "role": "admin"},
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


def _connecte(client):
    session = client.session
    session["token"] = FAUX_TOKEN
    session["mail"] = "cinema@example.com"
    session["role"] = "cinema"
    session.save()


def _connecte_admin(client):
    session = client.session
    session["token"] = FAUX_TOKEN_ADMIN
    session["mail"] = "admin@example.com"
    session["role"] = "admin"
    session.save()


@pytest.mark.django_db
def test_top10_redirige_si_pas_connecte(client):
    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 302


@pytest.mark.django_db
def test_top10_trie_par_entrees_predites_decroissant(client, monkeypatch):
    _connecte(client)
    faux_films = [
        {"id_oeuvre": 1, "nom_francais": "Petit film"},
        {"id_oeuvre": 2, "nom_francais": "Gros film"},
    ]
    fausses_predictions = {
        1: {
            "id_oeuvre": 1,
            "nom_francais": "Petit film",
            "entrees_premiere_semaine_predites": 1000,
        },
        2: {
            "id_oeuvre": 2,
            "nom_francais": "Gros film",
            "entrees_premiere_semaine_predites": 900000,
        },
    }
    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr(
        "predictions.views.appel_predict", lambda id_oeuvre, token: fausses_predictions[id_oeuvre]
    )

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    predictions = reponse.context["predictions"]
    assert [p["id_oeuvre"] for p in predictions] == [2, 1]


@pytest.mark.django_db
def test_top10_ignore_un_film_dont_la_prediction_echoue(client, monkeypatch):
    _connecte(client)
    faux_films = [
        {"id_oeuvre": 1, "nom_francais": "Film qui plante"},
        {"id_oeuvre": 2, "nom_francais": "Film ok"},
    ]

    def fausse_prediction(id_oeuvre, token):
        if id_oeuvre == 1:
            raise ErreurAPI("Film introuvable")
        return {"id_oeuvre": 2, "nom_francais": "Film ok", "entrees_premiere_semaine_predites": 500}

    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr("predictions.views.appel_predict", fausse_prediction)

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    predictions = reponse.context["predictions"]
    assert len(predictions) == 1
    assert predictions[0]["id_oeuvre"] == 2


@pytest.mark.django_db
def test_historique_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.get(reverse("predictions:historique"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_historique_accessible_pour_admin(client, monkeypatch):
    _connecte_admin(client)
    faux_historique = [
        {
            "nom_francais": "Film Test",
            "entrees_premiere_semaine_predites": 900,
            "entrees_premiere_semaine_reelles": 1000,
            "date_prediction": "2026-08-22T10:00:00",
            "ecart": -100,
        }
    ]
    monkeypatch.setattr("predictions.views.historique_predictions", lambda token: faux_historique)
    reponse = client.get(reverse("predictions:historique"))
    assert reponse.status_code == 200
    assert reponse.context["historique"] == faux_historique


@pytest.mark.django_db
def test_relancer_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.post(reverse("predictions:relancer"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_relancer_appelle_lapi_et_redirige(client, monkeypatch):
    _connecte_admin(client)
    appels = []
    monkeypatch.setattr(
        "predictions.views.appel_relancer",
        lambda token: appels.append(token) or {"nombre_predictions": 5},
    )
    reponse = client.post(reverse("predictions:relancer"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")
    assert appels == [FAUX_TOKEN_ADMIN]


@pytest.mark.django_db
def test_monitoring_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.get(reverse("predictions:monitoring"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_monitoring_affiche_les_metriques_parsees(client, monkeypatch):
    _connecte_admin(client)
    texte_prometheus = (
        'http_requests_total{handler="/predict",method="POST",status="2xx"} 3.0\n'
        'http_requests_total{handler="/health",method="GET",status="2xx"} 10.0\n'
    )
    monkeypatch.setattr("predictions.views.metriques_brutes", lambda token: texte_prometheus)
    reponse = client.get(reverse("predictions:monitoring"))
    assert reponse.status_code == 200
    metriques = reponse.context["metriques"]
    assert metriques["total_requetes"] == 13
    assert metriques["requetes_predict"] == 3
