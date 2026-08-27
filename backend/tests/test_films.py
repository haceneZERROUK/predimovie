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


def _creer_film(
    nom: str,
    date_sortie: date | None,
    synopsis: str | None = None,
    id_tmdb: int | None = 999999,
    annee_sortie: int | None = None,
) -> Oeuvre:
    """id_tmdb a une valeur par defaut (film "enrichi") : /films-a-venir
    exclut les films sans fiche TMDB (cf backend/films.py), la plupart des
    tests d'ici testent le filtre sur la date, pas sur la metadata."""
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
def film_jeudi():
    """Certaines sorties (avant-premieres, distribution limitee) tombent
    le jeudi de la semaine du mercredi a venir, pas le mercredi pile."""
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
    """Le samedi fait encore partie de la semaine de sortie (fenetre
    mercredi-samedi, 4 jours)."""
    oeuvre = _creer_film("Film Test Samedi", _prochain_mercredi() + timedelta(days=3))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_dimanche():
    """Le dimanche est deja la semaine suivante : ne doit pas ressortir
    (fenetre mercredi-samedi seulement)."""
    oeuvre = _creer_film("Film Test Dimanche", _prochain_mercredi() + timedelta(days=4))
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_sans_metadata():
    """Pas de fiche TMDB (id_tmdb=None) : pas assez d'infos pour une
    prediction fiable, cf le bug des 5 premiers films tous identiques."""
    oeuvre = _creer_film("Film Test Sans Metadata", _prochain_mercredi(), id_tmdb=None)
    yield oeuvre
    _supprimer_film(oeuvre)


@pytest.fixture
def film_ressortie():
    """Vieux film reprogramme des annees plus tard (ex: retrospective) :
    annee_sortie tres eloignee de la date de programmation."""
    oeuvre = _creer_film(
        "Film Test Ressortie", _prochain_mercredi(), id_tmdb=888888, annee_sortie=1990
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


def test_films_a_venir_exclut_le_film_deja_sorti_si_fenetre_normale_non_vide(
    film_pas_sorti, film_deja_sorti_sans_entrees
):
    """Un vieux film sans entrees n'est exclu que si la fenetre a venir a
    deja des films par ailleurs (sinon il sert justement de fallback,
    cf test_films_a_venir_fallback_sur_semaine_precedente_si_fenetre_vide)."""
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
    """Quand la fenetre mercredi-samedi a venir a deja des films, on ne
    va pas chercher plus loin (pas de fallback declenche inutilement)."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
    assert film_dans_2_mois.id_oeuvre not in ids


def test_films_a_venir_fallback_sur_semaine_precedente_si_fenetre_vide(film_deja_sorti_sans_entrees):
    """Si personne ne sort dans la fenetre mercredi-samedi a venir (le
    scraping n8n n'a pas encore rattrape la semaine), pas de page vide : on
    retombe sur la semaine precedente la plus recente qui a encore des films
    en attente de vrais resultats (entrees_premiere_semaine toujours NULL).
    On ne verifie pas que c'est precisement film_deja_sorti_sans_entrees qui
    ressort (la vraie base de dev peut deja avoir des films plus recents
    dans le meme cas, ce qui est le comportement voulu : le plus recent
    gagne) - juste qu'on n'a plus jamais une reponse vide des qu'un film
    en attente de resultats existe quelque part en base."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    assert len(reponse.json()) > 0


def test_films_a_venir_exclut_un_film_qui_sort_plus_tard_meme_si_fenetre_vide(film_dans_2_mois):
    """Le fallback ne regarde que vers le passe (semaine precedente), jamais
    vers un film isole loin dans le futur qui n'a aucun rapport avec ce que
    l'utilisateur programme cette semaine."""
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


def test_films_a_venir_exclut_le_dimanche_si_fenetre_normale_non_vide(film_pas_sorti, film_dimanche):
    """Le dimanche n'est deja plus dans la fenetre mercredi-samedi - tant
    que cette fenetre a par ailleurs des films (sinon le fallback pourrait
    legitimement remonter le dimanche comme faisant partie de la semaine
    precedente la plus proche)."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
    assert film_dimanche.id_oeuvre not in ids


def test_films_a_venir_exclut_le_film_sans_metadata(film_sans_metadata):
    """Cf le bug des 5 premiers films avec une prediction identique :
    sans fiche TMDB, pas assez d'infos pour une prediction fiable."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_sans_metadata.id_oeuvre not in ids


def test_films_a_venir_exclut_une_ressortie(film_ressortie):
    """Vieux film reprogramme des annees plus tard : pas une vraie
    nouvelle sortie."""
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_ressortie.id_oeuvre not in ids
