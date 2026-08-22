# Tests des routes admin : relancer les predictions, et l'historique
# predit/reel. Un compte cinema ne doit pas pouvoir y acceder (403).
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.security import creer_token
from database.base import SessionLocal
from database.models import Nature, Oeuvre, Prediction

client = TestClient(app)


def _token(role):
    return creer_token(mail="test@example.com", role=role)


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
        nom_francais="Film Test Relance",
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


@pytest.fixture
def film_sorti_avec_prediction():
    """Un film deja sorti (entrees connues) qui a une prediction stockee
    en base, pour tester la comparaison predit/reel."""
    session = SessionLocal()
    nature = session.query(Nature).filter_by(nom_nature="Film").first()
    if nature is None:
        nature = Nature(nom_nature="Film")
        session.add(nature)
        session.commit()
        session.refresh(nature)

    oeuvre = Oeuvre(
        nom_francais="Film Test Historique",
        nature=nature,
        entrees_premiere_semaine=1000,
    )
    session.add(oeuvre)
    session.commit()
    session.refresh(oeuvre)

    prediction = Prediction(
        id_oeuvre=oeuvre.id_oeuvre,
        nom_francais=oeuvre.nom_francais,
        entrees_premiere_semaine_predites=900,
        date_prediction=datetime.now(UTC),
    )
    session.add(prediction)
    session.commit()

    yield oeuvre
    session.delete(prediction)
    session.delete(oeuvre)
    session.commit()
    session.close()


def test_relancer_refuse_un_compte_cinema():
    reponse = client.post(
        "/predictions/relancer", headers={"Authorization": f"Bearer {_token('cinema')}"}
    )
    assert reponse.status_code == 403


def test_relancer_calcule_au_moins_une_prediction(film_pas_sorti):
    reponse = client.post(
        "/predictions/relancer", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 200
    assert reponse.json()["nombre_predictions"] >= 1

    session = SessionLocal()
    predictions = session.query(Prediction).filter_by(id_oeuvre=film_pas_sorti.id_oeuvre).all()
    assert len(predictions) == 1
    for p in predictions:
        session.delete(p)
    session.commit()
    session.close()


def test_historique_refuse_un_compte_cinema():
    reponse = client.get(
        "/predictions/historique", headers={"Authorization": f"Bearer {_token('cinema')}"}
    )
    assert reponse.status_code == 403


def test_historique_contient_le_film_sorti_avec_ecart(film_sorti_avec_prediction):
    reponse = client.get(
        "/predictions/historique", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 200
    lignes = [ligne for ligne in reponse.json() if ligne["nom_francais"] == "Film Test Historique"]
    assert len(lignes) == 1
    assert lignes[0]["entrees_premiere_semaine_predites"] == 900
    assert lignes[0]["entrees_premiere_semaine_reelles"] == 1000
    assert lignes[0]["ecart"] == -100
