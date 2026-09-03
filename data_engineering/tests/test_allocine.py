# Tests du scraper AlloCine, sur une vraie page sauvegardee dans fixtures/
from pathlib import Path

from data_engineering.allocine import extraire_films_de_la_semaine

DOSSIER_FIXTURES = Path(__file__).parent / "fixtures"


def _lire_fixture(nom_fichier: str) -> str:
    return (DOSSIER_FIXTURES / nom_fichier).read_text(encoding="utf-8")


def test_extraire_films_de_la_semaine_renvoie_des_films():
    html = _lire_fixture("allocine_semaine.html")
    films = extraire_films_de_la_semaine(html)

    assert len(films) > 0
    premier = films[0]
    assert premier["titre_francais"]
    assert isinstance(premier["id_allocine"], int)


def test_extraire_films_de_la_semaine_pas_de_doublons():
    html = _lire_fixture("allocine_semaine.html")
    films = extraire_films_de_la_semaine(html)

    ids = [film["id_allocine"] for film in films]
    assert len(ids) == len(set(ids))


def test_extraire_films_de_la_semaine_trouve_une_petite_sortie():
    """On verifie qu'on recupere bien les petites sorties, c'est tout
    l'interet d'AlloCine par rapport a JPBOX."""
    html = _lire_fixture("allocine_semaine.html")
    films = extraire_films_de_la_semaine(html)

    titres = [film["titre_francais"] for film in films]
    assert "Decorado" in titres
