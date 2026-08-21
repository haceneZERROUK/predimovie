# Tests des fonctions de construction de features (ml/data.py). Que du
# pandas en memoire, pas besoin de postgres pour ces tests-la.
import numpy as np
import pandas as pd
import pytest

from ml.data import _ajouter_features_entite, _ajouter_genres, _stats_par_entite


def test_stats_par_entite_lisse_les_entites_a_peu_de_films():
    # acteur "B" ne joue que dans 1 film, avec enormement d'entrees (1M) :
    # sans lissage son encodage collerait presque a log1p(1_000_000).
    oeuvres_train = pd.DataFrame(
        {
            "id_oeuvre": [1, 2, 3],
            "entrees_premiere_semaine": [100, 100, 1_000_000],
        }
    )
    liaisons = pd.DataFrame(
        {
            "id_oeuvre": [1, 2, 3],
            "nom_complet": ["A", "A", "B"],
        }
    )
    moyenne_globale = np.log1p(oeuvres_train["entrees_premiere_semaine"]).mean()

    stats = _stats_par_entite(liaisons, "nom_complet", oeuvres_train, moyenne_globale)

    moyenne_brute_b = np.log1p(1_000_000)
    # l'encodage de B doit etre tire vers la moyenne globale, donc beaucoup
    # plus proche d'elle que de sa propre moyenne brute (1 seul exemple)
    encodage_b = stats.loc["B", "encodage_cible"]
    assert abs(encodage_b - moyenne_globale) < abs(encodage_b - moyenne_brute_b)


def test_stats_par_entite_fait_plus_confiance_avec_plus_de_films():
    # meme "vrai" niveau (entrees_premiere_semaine identiques), mais A a
    # 2 films et B seulement 1 : B doit rester plus proche de la moyenne
    # globale que A (moins d'exemples = moins de confiance dans sa moyenne)
    oeuvres_train = pd.DataFrame(
        {
            "id_oeuvre": [1, 2, 3, 4],
            "entrees_premiere_semaine": [500_000, 500_000, 500_000, 1_000],
        }
    )
    liaisons = pd.DataFrame(
        {
            "id_oeuvre": [1, 2, 3, 4],
            "nom_complet": ["A", "A", "B", "C"],
        }
    )
    moyenne_globale = np.log1p(oeuvres_train["entrees_premiere_semaine"]).mean()

    stats = _stats_par_entite(liaisons, "nom_complet", oeuvres_train, moyenne_globale)

    ecart_a = abs(stats.loc["A", "encodage_cible"] - moyenne_globale)
    ecart_b = abs(stats.loc["B", "encodage_cible"] - moyenne_globale)
    assert ecart_a > ecart_b


def test_ajouter_features_entite_repli_moyenne_globale_pour_inconnu():
    # "Inconnu" n'apparait dans aucun film du train : sur le jeu de test,
    # il doit recevoir la moyenne globale, pas 0 (on n'a pas d'info sur
    # lui, mieux vaut rester neutre que pessimiste)
    oeuvres_train = pd.DataFrame(
        {
            "id_oeuvre": [1, 2],
            "entrees_premiere_semaine": [100_000, 200_000],
        }
    )
    liaisons_train = pd.DataFrame({"id_oeuvre": [1, 2], "nom_complet": ["A", "A"]})
    moyenne_globale = np.log1p(oeuvres_train["entrees_premiere_semaine"]).mean()
    stats = _stats_par_entite(liaisons_train, "nom_complet", oeuvres_train, moyenne_globale)

    oeuvres_test = pd.DataFrame({"id_oeuvre": [99], "entrees_premiere_semaine": [50_000]})
    liaisons_test = pd.DataFrame({"id_oeuvre": [99], "nom_complet": ["Inconnu"]})

    resultat = _ajouter_features_entite(
        oeuvres_test, liaisons_test, "nom_complet", "acteur", stats, moyenne_globale
    )

    # 1 credit sur ce film (l'acteur est bien liste), mais sa popularite
    # et son encodage retombent sur le repli neutre puisqu'il est inconnu du train
    assert resultat.loc[0, "acteur_nb"] == 1
    assert resultat.loc[0, "acteur_pop_max"] == 0
    assert resultat.loc[0, "acteur_encodage_cible"] == pytest.approx(moyenne_globale)


def test_ajouter_genres_construit_le_one_hot_et_compte_nb_genres():
    oeuvres = pd.DataFrame({"id_oeuvre": [1, 2]})
    genres = pd.DataFrame(
        {
            "id_oeuvre": [1, 1, 2],
            "nom_genre": ["Action", "Drame", "Comédie"],
        }
    )

    resultat, colonnes_genre = _ajouter_genres(oeuvres, genres, colonnes_genre_train=None)

    assert set(colonnes_genre) == {"genre_Action", "genre_Drame", "genre_Comédie"}
    assert resultat.loc[resultat["id_oeuvre"] == 1, "nb_genres"].item() == 2
    assert resultat.loc[resultat["id_oeuvre"] == 2, "nb_genres"].item() == 1


def test_ajouter_genres_reutilise_les_colonnes_du_train_pour_le_test():
    # le jeu de test ne doit jamais inventer une colonne de genre absente
    # du train (sinon X_train et X_test n'ont plus les memes colonnes)
    oeuvres_test = pd.DataFrame({"id_oeuvre": [1]})
    genres_test = pd.DataFrame({"id_oeuvre": [1], "nom_genre": ["Genre jamais vu au train"]})
    colonnes_genre_train = ["genre_Action", "genre_Drame"]

    resultat, colonnes_genre = _ajouter_genres(oeuvres_test, genres_test, colonnes_genre_train)

    assert colonnes_genre == colonnes_genre_train
    assert resultat.loc[0, "genre_Action"] == 0
    assert resultat.loc[0, "genre_Drame"] == 0
    assert resultat.loc[0, "nb_genres"] == 0
