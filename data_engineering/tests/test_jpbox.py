# Tests du scraper JPBOX, sur de vraies pages sauvegardees dans fixtures/
from pathlib import Path

from data_engineering.jpbox import (
    extraire_classement,
    extraire_films_du_calendrier,
    extraire_nb_salles_semaine1,
)

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
    """Sans lien vers la fiche, le parseur ne doit pas planter et juste
    renvoyer id_jpbox a None."""
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
    """Un film a souvent 2 liens sur la page (l'affiche et le titre),
    on ne doit le garder qu'une fois."""
    html = _lire_fixture("jpbox_calendrier.html")
    films = extraire_films_du_calendrier(html)

    ids = [film["id_jpbox"] for film in films]
    assert len(ids) == len(set(ids))


def test_extraire_nb_salles_semaine1_renvoie_la_premiere_ligne():
    """La fiche a une ligne par semaine, on ne veut que la premiere."""
    html = _lire_fixture("jpbox_fiche_film_semaines.html")
    nb_salles = extraire_nb_salles_semaine1(html)

    assert nb_salles == 472


def test_extraire_nb_salles_semaine1_renvoie_none_si_pas_de_tableau():
    """Un film pas encore sorti n'a pas de tableau, on renvoie None."""
    assert extraire_nb_salles_semaine1("<html><body>rien ici</body></html>") is None
