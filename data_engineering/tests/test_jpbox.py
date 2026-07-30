# Tests du scraper JPBOX : on utilise de vraies pages sauvegardées
# (fixtures/) pour ne pas dépendre du réseau ni du site en direct.
from pathlib import Path

from data_engineering.jpbox import extraire_classement, extraire_ids_films_a_venir

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


def test_extraire_ids_films_a_venir():
    html = _lire_fixture("jpbox_accueil.html")
    ids = extraire_ids_films_a_venir(html)

    assert len(ids) > 0
    assert all(isinstance(id_film, int) for id_film in ids)
