# Tests des fonctions du pipeline qui ne touchent ni la base ni le reseau
from datetime import date

from data_engineering.pipeline import _chercher_meme_sortie, prochain_mercredi
from database.models import Oeuvre


def test_prochain_mercredi_depuis_samedi():
    samedi = date(2026, 8, 22)
    assert prochain_mercredi(samedi) == date(2026, 8, 26)


def test_prochain_mercredi_depuis_mercredi():
    """Si on est deja mercredi, c'est le mercredi du jour qui compte."""
    mercredi = date(2026, 8, 26)
    assert prochain_mercredi(mercredi) == date(2026, 8, 26)


def test_prochain_mercredi_depuis_jeudi():
    jeudi = date(2026, 8, 27)
    assert prochain_mercredi(jeudi) == date(2026, 9, 2)


class _SessionFactice:
    """Une session reduite au strict necessaire : elle renvoie toujours la
    meme liste de candidats. Ca evite de monter une base pour tester une
    fonction qui ne fait qu'une comparaison de dates."""

    def __init__(self, candidats):
        self.candidats = candidats

    def query(self, _modele):
        return self

    def filter_by(self, **_criteres):
        return self

    def all(self):
        return self.candidats


def _oeuvre(id_tmdb, date_sortie):
    return Oeuvre(nom_francais="Un film", id_tmdb=id_tmdb, date_sortie=date_sortie)


def test_chercher_meme_sortie_retrouve_le_film_de_la_meme_semaine():
    """Le meme film expose sous deux id_jpbox : c'est le cas qui creait des
    lignes en double dans l'historique."""
    deja_en_base = _oeuvre(550, date(2026, 7, 15))
    session = _SessionFactice([deja_en_base])
    infos = {"id_tmdb": 550, "date_sortie": date(2026, 7, 15)}

    assert _chercher_meme_sortie(session, infos) is deja_en_base


def test_chercher_meme_sortie_ne_fusionne_pas_une_reprise():
    """Une reprise partage l'id_tmdb de la sortie d'origine mais sort des
    annees apres : ce sont deux exploitations differentes."""
    sortie_origine = _oeuvre(550, date(1999, 11, 10))
    session = _SessionFactice([sortie_origine])
    infos = {"id_tmdb": 550, "date_sortie": date(2026, 7, 15)}

    assert _chercher_meme_sortie(session, infos) is None


def test_chercher_meme_sortie_sans_date_ne_tranche_pas():
    """Sans date des deux cotes on ne peut pas savoir : on laisse le
    doublon plutot que de fusionner deux films differents."""
    sans_date = _oeuvre(550, None)
    session = _SessionFactice([sans_date])
    infos = {"id_tmdb": 550, "date_sortie": date(2026, 7, 15)}

    assert _chercher_meme_sortie(session, infos) is None


def test_chercher_meme_sortie_sans_tmdb_ne_cherche_pas():
    assert _chercher_meme_sortie(_SessionFactice([]), None) is None
    assert _chercher_meme_sortie(_SessionFactice([]), {"id_tmdb": None}) is None
