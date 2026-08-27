# Test du sous-modele salles (ml/salles.py). Juste la construction de
# features, pas d'entrainement reel ici (couvert par les tests du modele
# principal, meme logique).
import pandas as pd

from ml.salles import _construire_features


def test_construire_features_ajoute_le_mois_et_les_genres_en_one_hot():
    oeuvres = pd.DataFrame(
        {
            "id_oeuvre": [1, 2],
            "date_sortie": ["2026-08-26", "2026-01-14"],
            "budget": [1_000_000, None],
            "nb_salles_semaine1": [300, None],
        }
    )
    genres = pd.DataFrame({"id_oeuvre": [1, 2], "nom_genre": ["Action", "Comédie"]})

    resultat, colonnes_genre = _construire_features(oeuvres, genres)

    assert resultat.loc[resultat["id_oeuvre"] == 1, "mois_sortie"].item() == 8
    assert resultat.loc[resultat["id_oeuvre"] == 2, "mois_sortie"].item() == 1
    assert set(colonnes_genre) == {"genre_Action", "genre_Comédie"}
    assert resultat.loc[resultat["id_oeuvre"] == 1, "genre_Action"].item() == 1
    assert resultat.loc[resultat["id_oeuvre"] == 1, "genre_Comédie"].item() == 0


def test_construire_features_reutilise_les_colonnes_genre_fournies():
    oeuvres = pd.DataFrame({"id_oeuvre": [1], "date_sortie": ["2026-08-26"]})
    genres = pd.DataFrame({"id_oeuvre": [1], "nom_genre": ["Genre jamais vu"]})

    resultat, colonnes_genre = _construire_features(
        oeuvres, genres, colonnes_genre=["genre_Action", "genre_Drame"]
    )

    assert colonnes_genre == ["genre_Action", "genre_Drame"]
    assert resultat.loc[0, "genre_Action"] == 0
    assert resultat.loc[0, "genre_Drame"] == 0
