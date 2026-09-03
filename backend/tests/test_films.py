# Tests de /films-a-venir. On cree des films a differentes dates et on
# verifie lesquels ressortent, puis on nettoie.
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


def _creer_film(
    nom: str,
    date_sortie: date | None,
    synopsis: str | None = None,
    id_tmdb: int | None = 999999,
    annee_sortie: int | None = None,
) -> Oeuvre:
    """id_tmdb est rempli par defaut, sinon la route exclut le film et on
    ne testerait plus le filtre sur les dates."""
    session = SessionLocal()
    nature = _get_ou_creer_nature(session)
    oeuvre = Oeuvre(
        nom_francais=nom,
        nature=nature,
        entrees_premiere_semaine=None,
        date_sortie=date_sortie,
        synopsis=synopsis,
        id_tmdb=id_tmdb,
        annee_sortie=annee_sortie,
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
    """Film sorti la semaine derniere sans entrees renseignees."""
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
def film_jeudi():
    """Certains films sortent le jeudi et pas le mercredi."""
    oeuvre = _creer_film("Film Test Jeudi", _prochain_mercredi() + timedelta(days=1))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_vendredi():
    oeuvre = _creer_film("Film Test Vendredi", _prochain_mercredi() + timedelta(days=2))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_samedi():
    """Le samedi est encore dans la fenetre."""
    oeuvre = _creer_film("Film Test Samedi", _prochain_mercredi() + timedelta(days=3))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_dimanche():
    """Le dimanche est deja la semaine suivante, il ne doit pas sortir."""
    oeuvre = _creer_film("Film Test Dimanche", _prochain_mercredi() + timedelta(days=4))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_sans_metadata():
    """Film sans fiche TMDB, donc pas assez d'infos pour predire."""
    oeuvre = _creer_film("Film Test Sans Metadata", _prochain_mercredi(), id_tmdb=None)
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_ressortie():
    """Vieux film reprogramme, avec une annee_sortie tres eloignee."""
    oeuvre = _creer_film(
        "Film Test Ressortie", _prochain_mercredi(), id_tmdb=888888, annee_sortie=1990
    )
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_dans_2_mois():
    """Film qui sort dans 2 mois : trop loin, on ne veut que la semaine."""
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


def test_films_a_venir_exclut_le_film_deja_sorti_si_fenetre_normale_non_vide(
    film_pas_sorti, film_deja_sorti_sans_entrees
):
    """Le vieux film n'est exclu que si la fenetre a venir a deja des
    films, sinon c'est lui qui sert de fallback."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
    assert film_deja_sorti_sans_entrees.id_oeuvre not in ids


def test_films_a_venir_exclut_le_film_sans_date(film_sans_date):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_sans_date.id_oeuvre not in ids


def test_films_a_venir_exclut_un_film_qui_sort_plus_tard_si_fenetre_normale_non_vide(
    film_pas_sorti, film_dans_2_mois
):
    """Si la fenetre a deja des films, on ne va pas chercher plus loin."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
    assert film_dans_2_mois.id_oeuvre not in ids


def test_films_a_venir_fallback_sur_semaine_precedente_si_fenetre_vide(
    film_deja_sorti_sans_entrees,
):
    """Fenetre vide : on retombe sur la semaine d'avant au lieu de
    renvoyer une liste vide. On ne verifie pas quel film ressort
    exactement, la base peut en contenir de plus recents."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    assert len(reponse.json()) > 0


def test_films_a_venir_exclut_un_film_qui_sort_plus_tard_meme_si_fenetre_vide(film_dans_2_mois):
    """Le fallback ne regarde que vers le passe, jamais vers le futur."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_dans_2_mois.id_oeuvre not in ids


def test_films_a_venir_inclut_le_jeudi(film_jeudi):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_jeudi.id_oeuvre in ids


def test_films_a_venir_inclut_le_vendredi(film_vendredi):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_vendredi.id_oeuvre in ids


def test_films_a_venir_inclut_le_samedi(film_samedi):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_samedi.id_oeuvre in ids


def test_films_a_venir_exclut_le_dimanche_si_fenetre_normale_non_vide(
    film_pas_sorti, film_dimanche
):
    """Le dimanche sort de la fenetre, tant qu'elle a d'autres films."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
    assert film_dimanche.id_oeuvre not in ids


def test_films_a_venir_exclut_le_film_sans_metadata(film_sans_metadata):
    """Sans fiche TMDB on n'a pas assez d'infos, le film est ecarte."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_sans_metadata.id_oeuvre not in ids


def test_films_a_venir_exclut_une_ressortie(film_ressortie):
    """Une ressortie n'est pas une nouvelle sortie."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_ressortie.id_oeuvre not in ids
