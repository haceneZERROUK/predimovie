# Tests du module matching.py : pas besoin de réseau, on teste juste
# la logique de comparaison de titres.
from data_engineering.matching import meme_film, normaliser_titre, se_ressemblent


def test_normaliser_titre_enleve_accents_et_ponctuation():
    assert normaliser_titre("L'Odyssée !") == "odyssee"


def test_normaliser_titre_enleve_article_en_tete():
    assert normaliser_titre("The Odyssey") == "odyssey"
    assert normaliser_titre("Les Misérables") == "miserables"


def test_se_ressemblent_titres_identiques():
    assert se_ressemblent("Dune", "Dune") is True


def test_se_ressemblent_titres_differents():
    assert se_ressemblent("Dune", "Interstellar") is False


def test_se_ressemblent_malgre_accents_et_article():
    assert se_ressemblent("L'Odyssée", "Odyssee") is True


def test_meme_film_valide_titre_et_annee_proches():
    resultat_tmdb = {"title": "Dune", "release_date": "2021-09-15"}
    assert meme_film("Dune", 2021, resultat_tmdb) is True


def test_meme_film_refuse_annee_trop_eloignee():
    resultat_tmdb = {"title": "Dune", "release_date": "2010-01-01"}
    assert meme_film("Dune", 2021, resultat_tmdb) is False


def test_meme_film_refuse_titre_different():
    resultat_tmdb = {"title": "Interstellar", "release_date": "2021-09-15"}
    assert meme_film("Dune", 2021, resultat_tmdb) is False
