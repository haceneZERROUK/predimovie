# Tests du scraper JPBOX : on utilise de vraies pages sauvegardées
# (fixtures/) pour ne pas dépendre du réseau ni du site en direct.
from pathlib import Path

from data_engineering.jpbox import extraire_classement, extraire_films_du_calendrier

DOSSIER_FIXTURES = Path(__file__).parent / "fixtures"


def _lire_fixture(nom_fichier: str) -> str:
    return (DOSSIER_FIXTURES / nom_fichier).read_text(encoding="utf-8")


def test_extraire_classement_renvoie_des_films():
    html = _lire_fixture("jpbox_classement_semaine.html")
    films = extraire_classement(html)

    assert len(films) > 0
    premier = films[0]
    assert premier["titre_francais"]
    assert premier["entrees_semaine"] > 0
    assert premier["semaine_exploitation"] > 0


def test_extraire_classement_gere_les_films_sans_fiche():
    """Certaines lignes JPBOX n'ont pas de lien vers une fiche film :
    le parseur ne doit pas planter, juste renvoyer un id_jpbox à None."""
    html = _lire_fixture("jpbox_classement_semaine.html")
    films = extraire_classement(html)

    assert any(film["id_jpbox"] is None for film in films)


def test_extraire_films_du_calendrier():
    html = _lire_fixture("jpbox_calendrier.html")
    films = extraire_films_du_calendrier(html)

    assert len(films) > 0
    premier = films[0]
    assert premier["titre_francais"]
    assert isinstance(premier["id_jpbox"], int)


def test_extraire_films_du_calendrier_pas_de_doublons():
    """Un meme film peut avoir plusieurs liens sur la page (affiche +
    titre) : on ne doit le garder qu'une fois."""
    html = _lire_fixture("jpbox_calendrier.html")
    films = extraire_films_du_calendrier(html)

    ids = [film["id_jpbox"] for film in films]
    assert len(ids) == len(set(ids))
