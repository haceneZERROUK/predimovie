# Tests des vues de connexion/deconnexion. On ne tape jamais le vrai
# backend FastAPI ici : on remplace appel_login par une fausse fonction
# (monkeypatch) pour rester rapide et independant du reseau.
import re
from datetime import date

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
def test_landing_accessible_sans_etre_connecte(client):
    reponse = client.get(reverse("predictions:landing"))
    assert reponse.status_code == 200
    assert b"Predimovie" in reponse.content


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
def test_top10_convertit_la_date_iso_en_date_pour_l_affichage_francais(client, monkeypatch):
    """L'API renvoie une date ISO en texte ("2026-12-16") : la vue doit la
    convertir en vraie date pour que le template l'affiche en jj/mm/aaaa."""
    _connecte(client)
    faux_films = [{"id_oeuvre": 1, "nom_francais": "Film", "date_sortie": "2026-12-16"}]
    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr(
        "predictions.views.appel_predict",
        lambda id_oeuvre, token: {
            "id_oeuvre": 1,
            "nom_francais": "Film",
            "entrees_premiere_semaine_predites": 100,
        },
    )

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    assert reponse.context["predictions"][0]["date_sortie"] == date(2026, 12, 16)
    assert "16/12/2026" in reponse.content.decode()


@pytest.mark.django_db
def test_top10_affiche_le_synopsis_au_survol(client, monkeypatch):
    _connecte(client)
    faux_films = [{"id_oeuvre": 1, "nom_francais": "Film", "synopsis": "Un film mysterieux."}]
    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr(
        "predictions.views.appel_predict",
        lambda id_oeuvre, token: {
            "id_oeuvre": 1,
            "nom_francais": "Film",
            "entrees_premiere_semaine_predites": 100,
        },
    )

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    assert reponse.context["predictions"][0]["synopsis"] == "Un film mysterieux."
    assert "Un film mysterieux." in reponse.content.decode()


@pytest.mark.django_db
def test_top10_bulle_avec_message_de_repli_si_pas_de_synopsis(client, monkeypatch):
    """Meme sans synopsis en base (film pas matche sur TMDB), la bulle
    doit s'afficher au survol, avec un message de repli plutot que rien
    du tout : sinon on dirait que le survol ne marche pas sur ces films."""
    _connecte(client)
    faux_films = [{"id_oeuvre": 1, "nom_francais": "Film Sans Synopsis"}]
    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr(
        "predictions.views.appel_predict",
        lambda id_oeuvre, token: {
            "id_oeuvre": 1,
            "nom_francais": "Film Sans Synopsis",
            "entrees_premiere_semaine_predites": 100,
        },
    )

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    assert reponse.context["predictions"][0]["synopsis"] is None
    assert b'class="synopsis-bubble' in reponse.content
    assert "Synopsis non disponible" in reponse.content.decode()


@pytest.mark.django_db
def test_top10_bulle_s_ouvre_vers_le_haut_pour_les_dernieres_lignes(client, monkeypatch):
    """Pres du bas du tableau, la bulle doit s'ouvrir vers le haut (sinon
    elle sort de la page et se fait couper par le bas de l'ecran)."""
    _connecte(client)
    faux_films = [
        {"id_oeuvre": i, "nom_francais": f"Film {i}", "synopsis": f"Synopsis {i}"}
        for i in range(1, 7)
    ]
    monkeypatch.setattr("predictions.views.films_a_venir", lambda token: faux_films)
    monkeypatch.setattr(
        "predictions.views.appel_predict",
        lambda id_oeuvre, token: {
            "id_oeuvre": id_oeuvre,
            "nom_francais": f"Film {id_oeuvre}",
            # entrees decroissantes pour garder l'ordre 1..6 apres le tri
            "entrees_premiere_semaine_predites": 1000 - id_oeuvre,
        },
    )

    reponse = client.get(reverse("predictions:top10"))
    assert reponse.status_code == 200
    contenu = reponse.content.decode()

    # chaque bulle "<span class="synopsis-bubble ... top-full|bottom-full ...">Synopsis N</span>"
    bulles = re.findall(r'class="synopsis-bubble([^"]*)"[^>]*>\s*Synopsis (\d)', contenu)
    classes_par_film = {numero: classes for classes, numero in bulles}
    assert "top-full" in classes_par_film["1"]
    assert "bottom-full" in classes_par_film["6"]


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
def test_comptes_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.get(reverse("predictions:comptes"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_comptes_accessible_pour_admin(client, monkeypatch):
    _connecte_admin(client)
    faux_comptes = [
        {
            "id_compte": 1,
            "mail": "cinema@example.com",
            "nom_cinema": "Cinema Test",
            "date_inscription": "2026-08-22",
            "derniere_connexion": None,
            "statut_compte": True,
        }
    ]
    monkeypatch.setattr("predictions.views.lister_comptes", lambda token: faux_comptes)
    reponse = client.get(reverse("predictions:comptes"))
    assert reponse.status_code == 200
    assert reponse.context["comptes"][0]["mail"] == "cinema@example.com"
    assert reponse.context["comptes"][0]["date_inscription"] == date(2026, 8, 22)


@pytest.mark.django_db
def test_creer_compte_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.get(reverse("predictions:creer_compte"))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_creer_compte_get_affiche_le_formulaire(client):
    _connecte_admin(client)
    reponse = client.get(reverse("predictions:creer_compte"))
    assert reponse.status_code == 200
    assert b"nom_cinema" in reponse.content


@pytest.mark.django_db
def test_creer_compte_post_cree_et_redirige(client, monkeypatch):
    _connecte_admin(client)
    appels = []
    monkeypatch.setattr(
        "predictions.views.appel_creer_compte",
        lambda mail, mot_de_passe, nom_cinema, token: appels.append(
            (mail, mot_de_passe, nom_cinema)
        ),
    )
    reponse = client.post(
        reverse("predictions:creer_compte"),
        {
            "mail": "nouveau@example.com",
            "mot_de_passe": "azerty123",
            "nom_cinema": "Cinema Le Nouveau",
        },
    )
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:comptes")
    assert appels == [("nouveau@example.com", "azerty123", "Cinema Le Nouveau")]


@pytest.mark.django_db
def test_creer_compte_post_affiche_l_erreur_si_mail_deja_pris(client, monkeypatch):
    _connecte_admin(client)

    def _echoue(mail, mot_de_passe, nom_cinema, token):
        raise ErreurAPI("Un compte existe deja avec ce mail")

    monkeypatch.setattr("predictions.views.appel_creer_compte", _echoue)
    reponse = client.post(
        reverse("predictions:creer_compte"),
        {"mail": "deja@example.com", "mot_de_passe": "azerty123", "nom_cinema": "Doublon"},
    )
    assert reponse.status_code == 200
    assert b"nom_cinema" in reponse.content


@pytest.mark.django_db
def test_supprimer_compte_refuse_un_compte_cinema(client):
    _connecte(client)
    reponse = client.post(reverse("predictions:supprimer_compte", args=[1]))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:accueil")


@pytest.mark.django_db
def test_supprimer_compte_appelle_l_api_et_redirige(client, monkeypatch):
    _connecte_admin(client)
    appels = []
    monkeypatch.setattr(
        "predictions.views.appel_supprimer_compte",
        lambda id_compte, token: appels.append(id_compte),
    )
    reponse = client.post(reverse("predictions:supprimer_compte", args=[42]))
    assert reponse.status_code == 302
    assert reponse.url == reverse("predictions:comptes")
    assert appels == [42]


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
