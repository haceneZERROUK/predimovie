# Tests des routes admin : relance des predictions et historique
# predit/reel. Un compte cinema ne doit pas y avoir acces.
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
    """Un film deja sorti avec une prediction en base, pour comparer
    predit et reel."""
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
        # il faut etre dans les 4 dernieres semaines, sinon la route ne
        # renvoie pas le film
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
    """Une semaine sans sortie doit renvoyer une liste vide."""
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
    """Si le film a plusieurs predictions, on ne garde que la derniere."""
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


@pytest.fixture
def _nature():
    session = SessionLocal()
    nature = session.query(Nature).filter_by(nom_nature="Film").first()
    if nature is None:
        nature = Nature(nom_nature="Film")
        session.add(nature)
        session.commit()
        session.refresh(nature)
    id_nature = nature.id_nature
    session.close()
    return id_nature


@pytest.fixture
def film_collecte_deux_fois(_nature):
    """Le meme film entre deux fois en base sous deux id_jpbox differents :
    meme id_tmdb, meme semaine, mais des entrees reelles differentes."""
    session = SessionLocal()
    doublons = [
        Oeuvre(
            nom_francais="Film Test Doublon",
            id_nature=_nature,
            id_tmdb=987654,
            id_jpbox=111,
            date_sortie=date.today(),
            annee_sortie=date.today().year,
            entrees_premiere_semaine=800000,
        ),
        Oeuvre(
            nom_francais="Film Test Doublon",
            id_nature=_nature,
            id_tmdb=987654,
            id_jpbox=222,
            date_sortie=date.today(),
            annee_sortie=date.today().year,
            entrees_premiere_semaine=200000,
        ),
    ]
    session.add_all(doublons)
    session.commit()
    yield
    for oeuvre in doublons:
        session.delete(oeuvre)
    session.commit()
    session.close()


@pytest.fixture
def reprise_en_salle(_nature):
    """Un film de 1999 ressorti aujourd'hui : c'est une reprise."""
    session = SessionLocal()
    oeuvre = Oeuvre(
        nom_francais="Film Test Reprise",
        id_nature=_nature,
        id_tmdb=123456,
        date_sortie=date.today(),
        annee_sortie=1999,
        entrees_premiere_semaine=5000,
    )
    session.add(oeuvre)
    session.commit()
    yield
    session.delete(oeuvre)
    session.commit()
    session.close()


def _historique():
    reponse = client.get(
        "/predictions/historique", headers={"Authorization": f"Bearer {_token('admin')}"}
    )
    assert reponse.status_code == 200
    return reponse.json()["predictions"]


def test_historique_ne_montre_quune_ligne_par_film_collecte_deux_fois(film_collecte_deux_fois):
    """Deux lignes en base pour le meme film ne doivent en donner qu'une a
    l'ecran, celle de l'exploitation principale."""
    lignes = [x for x in _historique() if x["nom_francais"] == "Film Test Doublon"]
    assert len(lignes) == 1
    assert lignes[0]["entrees_premiere_semaine_reelles"] == 800000


def test_historique_ecarte_les_reprises_comme_le_classement(reprise_en_salle):
    """Une reprise est deja ecartee du classement : elle ne doit pas
    reapparaitre dans l'historique."""
    assert [x for x in _historique() if x["nom_francais"] == "Film Test Reprise"] == []


@pytest.fixture
def suite_et_original(_nature):
    """Deux films differents que le rapprochement TMDB a colles sur la meme
    fiche : c'est le cas reel de "Toy Story 5" pointant sur "Toy Story".
    Les deux doivent rester visibles."""
    session = SessionLocal()
    films = [
        Oeuvre(
            nom_francais="Film Test Original",
            id_nature=_nature,
            id_tmdb=987655,
            date_sortie=date.today(),
            annee_sortie=date.today().year,
            entrees_premiere_semaine=700000,
        ),
        Oeuvre(
            nom_francais="Film Test Original 2",
            id_nature=_nature,
            id_tmdb=987655,
            date_sortie=date.today(),
            annee_sortie=date.today().year,
            entrees_premiere_semaine=300000,
        ),
    ]
    session.add_all(films)
    session.commit()
    yield
    for film in films:
        session.delete(film)
    session.commit()
    session.close()


def test_historique_garde_une_suite_qui_partage_la_fiche_tmdb(suite_et_original):
    """Regrouper sur id_tmdb ferait disparaitre la suite de l'ecran."""
    titres = [x["nom_francais"] for x in _historique()]
    assert "Film Test Original" in titres
    assert "Film Test Original 2" in titres
