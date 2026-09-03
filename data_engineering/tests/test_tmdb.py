# Test de date_sortie_france avec une fausse reponse TMDB, pas de reseau
from data_engineering.tmdb import date_sortie_france


def test_date_sortie_france_prend_la_date_theatrale():
    resultats = [
        {
            "iso_3166_1": "US",
            "release_dates": [{"type": 3, "release_date": "2026-12-18T00:00:00.000Z"}],
        },
        {
            "iso_3166_1": "FR",
            "release_dates": [{"type": 3, "release_date": "2026-12-16T00:00:00.000Z"}],
        },
    ]
    assert date_sortie_france(resultats) == "2026-12-16"


def test_date_sortie_france_ignore_avant_premiere():
    """Le type 2 c'est une avant-premiere, on veut le type 3."""
    resultats = [
        {
            "iso_3166_1": "FR",
            "release_dates": [
                {"type": 2, "release_date": "2026-12-01T00:00:00.000Z"},
                {"type": 3, "release_date": "2026-12-16T00:00:00.000Z"},
            ],
        }
    ]
    assert date_sortie_france(resultats) == "2026-12-16"


def test_date_sortie_france_renvoie_none_si_pas_de_france():
    resultats = [
        {
            "iso_3166_1": "US",
            "release_dates": [{"type": 3, "release_date": "2027-06-30T00:00:00.000Z"}],
        }
    ]
    assert date_sortie_france(resultats) is None


def test_date_sortie_france_renvoie_none_si_pas_de_sortie_salle():
    """La France est listee mais sans sortie nationale : on renvoie None."""
    resultats = [
        {
            "iso_3166_1": "FR",
            "release_dates": [{"type": 2, "release_date": "2026-12-01T00:00:00.000Z"}],
        }
    ]
    assert date_sortie_france(resultats) is None
