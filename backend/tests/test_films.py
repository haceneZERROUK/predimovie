# Test de /films-a-venir : cree un vrai film sans entrees connues (donc
# "pas encore sorti"), verifie qu'il ressort bien dans la liste, et
# nettoie derriere lui.
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import creer_token
from database.base import SessionLocal
from database.models import Nature, Oeuvre

client = TestClient(app)


@pytest.fixture
def film_pas_sorti():
    session = SessionLocal()
    nature = session.query(Nature).filter_by(nom_nature="Film").first()
    if nature is None:
        nature = Nature(nom_nature="Film")
        session.add(nature)
        session.commit()
        session.refresh(nature)

    oeuvre = Oeuvre(
        nom_francais="Film Test Pas Encore Sorti",
        nature=nature,
        entrees_premiere_semaine=None,
    )
    session.add(oeuvre)
    session.commit()
    session.refresh(oeuvre)
    yield oeuvre
    session.delete(oeuvre)
    session.commit()
    session.close()


def test_films_a_venir_sans_token():
    reponse = client.get("/films-a-venir")
    assert reponse.status_code in (401, 403)


def test_films_a_venir_liste_bien_le_film_pas_sorti(film_pas_sorti):
    token = creer_token(mail="cinema@example.com", role="cinema")
    reponse = client.get("/films-a-venir", headers={"Authorization": f"Bearer {token}"})
    assert reponse.status_code == 200
    ids = [f["id_oeuvre"] for f in reponse.json()]
    assert film_pas_sorti.id_oeuvre in ids
