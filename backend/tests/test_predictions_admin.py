# Tests des routes admin : relancer les predictions, et l'historique
# predit/reel. Un compte cinema ne doit pas pouvoir y acceder (403).
from datetime import UTC, date, datetime

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
        # dans la fenetre par defaut de /predictions/historique (4 dernieres
        # semaines) : sans ca, le film ne ressortirait pas du tout du test
        date_sortie=date.today(),
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
    predictions = reponse.json()["predictions"]
    lignes = [ligne for ligne in predictions if ligne["nom_francais"] == "Film Test Historique"]
    assert len(lignes) == 1
    assert lignes[0]["entrees_premiere_semaine_predites"] == 900
    assert lignes[0]["entrees_premiere_semaine_reelles"] == 1000
    assert lignes[0]["ecart"] == -100


def test_historique_liste_la_semaine_dans_semaines_disponibles(film_sorti_avec_prediction):
    reponse = client.get(
        "/predictions/historique", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert date.today().isoformat() in reponse.json()["semaines_disponibles"]


def test_historique_filtre_par_semaine_exclut_les_autres(film_sorti_avec_prediction):
    """Une semaine sans aucune sortie ne doit renvoyer aucune ligne, meme
    si d'autres films existent par ailleurs dans la base."""
    autre_semaine = date(2020, 1, 1).isoformat()  # forcement differente d'aujourd'hui
    reponse = client.get(
        "/predictions/historique",
        params={"semaine": autre_semaine},
        headers={"Authorization": f"Bearer {_token('admin')}"},
    )
    assert reponse.status_code == 200
    noms = [ligne["nom_francais"] for ligne in reponse.json()["predictions"]]
    assert "Film Test Historique" not in noms


def test_historique_ne_garde_que_la_derniere_prediction_par_film(film_sorti_avec_prediction):
    """Si le film a ete "relance" plusieurs fois, on ne veut que la
    prediction la plus recente dans l'historique, pas chaque essai."""
    session = SessionLocal()
    session.add(
        Prediction(
            id_oeuvre=film_sorti_avec_prediction.id_oeuvre,
            nom_francais=film_sorti_avec_prediction.nom_francais,
            entrees_premiere_semaine_predites=1200,
            date_prediction=datetime.now(UTC),
        )
    )
    session.commit()
    session.close()

    reponse = client.get(
        "/predictions/historique", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    lignes = [
        ligne
        for ligne in reponse.json()["predictions"]
        if ligne["nom_francais"] == "Film Test Historique"
    ]
    assert len(lignes) == 1
    assert lignes[0]["entrees_premiere_semaine_predites"] == 1200

    session = SessionLocal()
    session.query(Prediction).filter_by(
        id_oeuvre=film_sorti_avec_prediction.id_oeuvre,
        entrees_premiere_semaine_predites=1200,
    ).delete()
    session.commit()
    session.close()
