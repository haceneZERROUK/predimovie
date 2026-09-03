# Tests de la construction des features. Que du pandas en memoire, pas
# de postgres.
import numpy as np
import pandas as pd
import pytest

from ml.data import _ajouter_features_entite, _ajouter_genres, _stats_par_entite


def test_stats_par_entite_lisse_les_entites_a_peu_de_films():
    # l'acteur B n'a qu'un film, avec 1M d'entrees : sans lissage son
    # encodage collerait a log1p(1_000_000)
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
    # son encodage doit etre tire vers la moyenne globale
    encodage_b = stats.loc["B", "encodage_cible"]
    assert abs(encodage_b - moyenne_globale) < abs(encodage_b - moyenne_brute_b)


def test_stats_par_entite_fait_plus_confiance_avec_plus_de_films():
    # A et B ont les memes entrees, mais A a 2 films et B un seul : B doit
    # rester plus proche de la moyenne globale
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
    # "Inconnu" n'est dans aucun film du train, il doit recevoir la
    # moyenne globale et pas 0
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

    # l'acteur est bien compte sur le film, mais sa popularite et son
    # encodage retombent sur les valeurs neutres
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
    # le test ne doit pas inventer une colonne de genre absente du train,
    # sinon X_train et X_test n'ont plus les memes colonnes
    oeuvres_test = pd.DataFrame({"id_oeuvre": [1]})
    genres_test = pd.DataFrame({"id_oeuvre": [1], "nom_genre": ["Genre jamais vu au train"]})
    colonnes_genre_train = ["genre_Action", "genre_Drame"]

    resultat, colonnes_genre = _ajouter_genres(oeuvres_test, genres_test, colonnes_genre_train)

    assert colonnes_genre == colonnes_genre_train
    assert resultat.loc[0, "genre_Action"] == 0
    assert resultat.loc[0, "genre_Drame"] == 0
    assert resultat.loc[0, "nb_genres"] == 0
