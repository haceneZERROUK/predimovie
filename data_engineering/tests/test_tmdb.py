# Test de date_sortie_france() : pas besoin de reseau, on lui donne
# directement une reponse TMDB /release_dates factice.
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
    """Type 2 = "Premiere" (avant-premiere) : on veut la vraie sortie
    nationale (type 3), pas la date d'un evenement presse isole."""
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
    """La France est bien listee mais avec seulement une avant-premiere,
    pas de vraie sortie nationale (type 3) : pas de date fiable."""
    resultats = [
        {
            "iso_3166_1": "FR",
            "release_dates": [{"type": 2, "release_date": "2026-12-01T00:00:00.000Z"}],
        }
    ]
    assert date_sortie_france(resultats) is None
