# Tests du nettoyage des films entres plusieurs fois en base. Celui-la
# touche la base, vu que c'est justement ce qu'il supprime.
from datetime import UTC, date, datetime

import pytest

from data_engineering.nettoyer_doublons import _groupes_de_doublons, main
from database.base import SessionLocal
from database.models import Nature, Oeuvre, Prediction

TMDB_DOUBLON = 990001
TMDB_REPRISE = 990002


@pytest.fixture
def _id_nature():
    session = SessionLocal()
    nature = session.query(Nature).filter_by(nom_nature="Film").first()
    if nature is None:
        nature = Nature(nom_nature="Film")
        session.add(nature)
        session.commit()
        session.refresh(nature)
    identifiant = nature.id_nature
    session.close()
    return identifiant


def _vider(session):
    """Enleve ce qu'aurait pu laisser une execution interrompue, sinon
    l'insertion casse sur la contrainte d'unicite d'id_jpbox."""
    anciennes = session.query(Oeuvre).filter(Oeuvre.id_tmdb.in_((TMDB_DOUBLON, TMDB_REPRISE))).all()
    for oeuvre in anciennes:
        session.query(Prediction).filter_by(id_oeuvre=oeuvre.id_oeuvre).delete()
        session.delete(oeuvre)
    session.commit()


def _creer(session, id_nature, id_tmdb, id_jpbox, jour, entrees):
    oeuvre = Oeuvre(
        nom_francais="Film Test Nettoyage",
        id_nature=id_nature,
        id_tmdb=id_tmdb,
        id_jpbox=id_jpbox,
        date_sortie=jour,
        annee_sortie=jour.year,
        entrees_premiere_semaine=entrees,
    )
    session.add(oeuvre)
    session.commit()
    session.refresh(oeuvre)
    return oeuvre


@pytest.fixture
def base_avec_doublons(_id_nature):
    """Deux lignes pour le meme film la meme semaine (un doublon), plus une
    reprise du meme film des annees apres (qui doit survivre)."""
    session = SessionLocal()
    _vider(session)
    jour = date(2026, 7, 15)
    principal = _creer(session, _id_nature, TMDB_DOUBLON, 900001, jour, 1841065)
    secondaire = _creer(session, _id_nature, TMDB_DOUBLON, 900002, jour, 445363)
    # une prediction accrochee a la ligne qui va disparaitre : sans
    # suppression prealable la contrainte de cle etrangere sauterait
    session.add(
        Prediction(
            id_oeuvre=secondaire.id_oeuvre,
            nom_francais=secondaire.nom_francais,
            entrees_premiere_semaine_predites=1381660,
            date_prediction=datetime.now(UTC),
        )
    )
    origine = _creer(session, _id_nature, TMDB_REPRISE, 900003, date(1999, 11, 10), 50000)
    reprise = _creer(session, _id_nature, TMDB_REPRISE, 900004, date(2026, 7, 15), 5000)
    session.commit()
    # on retient les identifiants avant de fermer : apres, les objets ne
    # sont plus rattaches a une session et ne repondent plus
    identifiants = {
        "principal": principal.id_oeuvre,
        "secondaire": secondaire.id_oeuvre,
        "origine": origine.id_oeuvre,
        "reprise": reprise.id_oeuvre,
    }
    session.close()

    yield identifiants

    session = SessionLocal()
    _vider(session)
    session.close()


def test_les_deux_lignes_de_la_meme_semaine_forment_un_groupe(base_avec_doublons):
    session = SessionLocal()
    groupes = _groupes_de_doublons(session)
    session.close()

    concernes = [g for g in groupes if g[0].id_tmdb == TMDB_DOUBLON]
    assert len(concernes) == 1
    assert len(concernes[0]) == 2


def test_une_reprise_nest_pas_vue_comme_un_doublon(base_avec_doublons):
    """Meme id_tmdb mais des annees d'ecart : ce sont deux exploitations."""
    session = SessionLocal()
    groupes = _groupes_de_doublons(session)
    session.close()

    assert [g for g in groupes if g[0].id_tmdb == TMDB_REPRISE] == []


def test_sans_appliquer_rien_nest_supprime(base_avec_doublons):
    main(appliquer=False)

    session = SessionLocal()
    restants = session.query(Oeuvre).filter_by(id_tmdb=TMDB_DOUBLON).count()
    session.close()
    assert restants == 2


def test_appliquer_garde_la_ligne_qui_a_le_plus_d_entrees(base_avec_doublons):
    main(appliquer=True)

    session = SessionLocal()
    restants = session.query(Oeuvre).filter_by(id_tmdb=TMDB_DOUBLON).all()
    ids_restants = [o.id_oeuvre for o in restants]
    # la prediction de la ligne supprimee doit partir avec elle
    predictions_orphelines = (
        session.query(Prediction).filter_by(id_oeuvre=base_avec_doublons["secondaire"]).count()
    )
    session.close()

    assert ids_restants == [base_avec_doublons["principal"]]
    assert restants[0].entrees_premiere_semaine == 1841065
    assert predictions_orphelines == 0


def test_appliquer_ne_touche_pas_a_la_reprise(base_avec_doublons):
    main(appliquer=True)

    session = SessionLocal()
    restants = session.query(Oeuvre).filter_by(id_tmdb=TMDB_REPRISE).count()
    session.close()
    assert restants == 2
