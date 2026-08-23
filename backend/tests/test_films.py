# Test de /films-a-venir : cree de vrais films (mercredi prochain, deja
# sorti mais entrees manquantes, dans 2 mois, sans date du tout), verifie
# que seul celui du mercredi prochain ressort, et nettoie derriere lui.
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.films import _prochain_mercredi
from backend.main import app
from backend.security import creer_token
from database.base import SessionLocal
from database.models import Nature, Oeuvre

client = TestClient(app)


def _get_ou_creer_nature(session):
    nature = session.query(Nature).filter_by(nom_nature="Film").first()
    if nature is None:
        nature = Nature(nom_nature="Film")
        session.add(nature)
        session.commit()
        session.refresh(nature)
    return nature


def _creer_film(nom: str, date_sortie: date | None, synopsis: str | None = None) -> Oeuvre:
    session = SessionLocal()
    nature = _get_ou_creer_nature(session)
    oeuvre = Oeuvre(
        nom_francais=nom,
        nature=nature,
        entrees_premiere_semaine=None,
        date_sortie=date_sortie,
        synopsis=synopsis,
    )
    session.add(oeuvre)
    session.commit()
    session.refresh(oeuvre)
    session.close()
    return oeuvre


def _supprimer_film(oeuvre: Oeuvre) -> None:
    session = SessionLocal()
    session.delete(session.merge(oeuvre))
    session.commit()
    session.close()


@pytest.fixture
def film_pas_sorti():
    oeuvre = _creer_film("Film Test Pas Encore Sorti", _prochain_mercredi())
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_deja_sorti_sans_entrees():
    """Film sorti la semaine derniere mais dont les entrees n'ont jamais
    ete renseignees : ne doit pas etre traite comme "a venir"."""
    oeuvre = _creer_film("Film Test Deja Sorti", date.today() - timedelta(days=7))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_sans_date():
    oeuvre = _creer_film("Film Test Sans Date", None)
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_avec_synopsis():
    oeuvre = _creer_film(
        "Film Test Avec Synopsis", _prochain_mercredi(), synopsis="Un synopsis de test."
    )
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_dans_2_mois():
    """Film pas encore sorti mais pas du mercredi a venir non plus (sort
    dans 2 mois) : on ne veut que les sorties de la semaine, pas tout ce
    qui est dans le futur."""
    oeuvre = _creer_film("Film Test Dans 2 Mois", _prochain_mercredi() + timedelta(days=60))
    yield oeuvre
    _supprimer_film(oeuvre)


def test_films_a_venir_sans_token():
    reponse = client.get("/films-a-venir")
    assert reponse.status_code in (401, 403)


def test_films_a_venir_liste_bien_le_film_pas_sorti(film_pas_sorti):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids


def test_films_a_venir_renvoie_le_synopsis(film_avec_synopsis):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    film = next(f for f in reponse.json() if f["id_oeuvre"] == film_avec_synopsis.id_oeuvre)
    assert film["synopsis"] == "Un synopsis de test."


def test_films_a_venir_exclut_le_film_deja_sorti(film_deja_sorti_sans_entrees):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_deja_sorti_sans_entrees.id_oeuvre not in ids


def test_films_a_venir_exclut_le_film_sans_date(film_sans_date):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_sans_date.id_oeuvre not in ids


def test_films_a_venir_exclut_un_film_qui_sort_plus_tard(film_dans_2_mois):
    """On veut les sorties du mercredi a venir, pas n'importe quel film
    pas encore sorti (sinon on remonte des films qui sortent dans des mois)."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_dans_2_mois.id_oeuvre not in ids
