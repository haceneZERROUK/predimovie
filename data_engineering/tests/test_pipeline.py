# Tests des petites fonctions pures du pipeline (pas besoin de DB/reseau).
from datetime import date

from data_engineering.pipeline import prochain_mercredi


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
