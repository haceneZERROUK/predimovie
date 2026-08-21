# Charge les films depuis postgres et construit le tableau de features
# pour l'entrainement. Separe de train.py pour pouvoir le tester tout seul.
#
# Important : le split train/test se fait AVANT de calculer les features
# d'encodage cible (moyenne d'entrees par acteur/realisateur/etc). Sinon
# la moyenne calculee sur un acteur inclurait la reponse des films du test,
# et le modele "tricherait" sans qu'on s'en rende compte (data leakage).
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from database.base import get_engine

# on garde que les films dont on connait vraiment le resultat en salle
# (les entrees a 0 c'est surtout des vieux films des annees 90 avec des
# donnees jpbox pas fiables, cf audit de la base)
REQUETE_OEUVRES = """
SELECT id_oeuvre, annee_sortie, note_tmdb, note_imdb,
       mot_cle_1, mot_cle_2, mot_cle_3, entrees_premiere_semaine
FROM oeuvre
WHERE entrees_premiere_semaine IS NOT NULL
  AND entrees_premiere_semaine > 0;
"""

REQUETE_GENRES = """
SELECT go.id_oeuvre, g.nom_genre
FROM genre_oeuvre go JOIN genre g ON g.id_genre = go.id_genre;
"""

REQUETE_ACTEURS = """
SELECT ao.id_oeuvre, a.prenom || ' ' || a.nom AS nom_complet
FROM acteur_oeuvre ao JOIN acteur a ON a.id_acteur = ao.id_acteur;
"""

REQUETE_REALISATEURS = """
SELECT ro.id_oeuvre, r.prenom || ' ' || r.nom AS nom_complet
FROM realisateur_oeuvre ro JOIN realisateur r ON r.id_realisateur = ro.id_realisateur;
"""

REQUETE_PRODUCTIONS = """
SELECT po.id_oeuvre, p.nom_societe AS nom_production
FROM production_oeuvre po JOIN production p ON p.id_production = po.id_production;
"""


def charger_donnees_brutes():
    """Charge tout depuis postgres, sans aucun calcul qui touche la cible.
    Le split train/test se fait juste apres, sur ces tables brutes."""
    engine = get_engine()

    oeuvres = pd.read_sql(REQUETE_OEUVRES, engine)
    genres = pd.read_sql(REQUETE_GENRES, engine)
    acteurs = pd.read_sql(REQUETE_ACTEURS, engine)
    realisateurs = pd.read_sql(REQUETE_REALISATEURS, engine)
    productions = pd.read_sql(REQUETE_PRODUCTIONS, engine)

    for colonne in ["annee_sortie", "note_tmdb", "note_imdb"]:
        oeuvres[colonne] = oeuvres[colonne].fillna(oeuvres[colonne].median())

    return oeuvres, genres, acteurs, realisateurs, productions


# lissage bayesien de l'encodage cible : plus une personne/societe a peu de
# films dans le train, plus on tire sa valeur vers la moyenne globale plutot
# que de faire confiance a son historique (souvent 1 seul film => sans ca,
# l'encodage devient quasiment la vraie reponse de ce film, pas fiable)
POIDS_LISSAGE = 8


def _stats_par_entite(
    liaisons: pd.DataFrame, colonne_nom: str, oeuvres_train: pd.DataFrame, moyenne_cible_globale: float
) -> pd.DataFrame:
    """Calcule, pour chaque personne/societe/genre, deux choses a partir
    UNIQUEMENT des films du train : sa popularite (dans combien de films
    elle apparait) et son encodage cible lisse (la moyenne en log des
    entrees des films ou elle apparait, ramenee vers la moyenne globale
    quand on a peu d'exemples). L'encodage cible est un signal bien plus
    direct que la popularite pour dire si "ce nom fait vendre des billets"."""
    entrees_log_par_film = np.log1p(
        oeuvres_train.set_index("id_oeuvre")["entrees_premiere_semaine"]
    )
    liaisons_train = liaisons[liaisons["id_oeuvre"].isin(oeuvres_train["id_oeuvre"])].copy()
    liaisons_train["entrees_log"] = liaisons_train["id_oeuvre"].map(entrees_log_par_film)

    stats = liaisons_train.groupby(colonne_nom).agg(
        popularite=("id_oeuvre", "count"),
        moyenne_brute=("entrees_log", "mean"),
    )
    # formule du lissage : (nb_films * moyenne_de_la_personne + poids * moyenne_globale) / (nb_films + poids)
    # ex: 1 seul film -> l'encodage reste tres proche de la moyenne globale
    #     50 films -> l'encodage fait presque entierement confiance a sa propre moyenne
    stats["encodage_cible"] = (
        stats["popularite"] * stats["moyenne_brute"] + POIDS_LISSAGE * moyenne_cible_globale
    ) / (stats["popularite"] + POIDS_LISSAGE)
    return stats[["popularite", "encodage_cible"]]


def _ajouter_features_entite(
    oeuvres: pd.DataFrame, liaisons: pd.DataFrame, colonne_nom: str, prefixe: str,
    stats: pd.DataFrame, moyenne_cible_globale: float,
) -> pd.DataFrame:
    """Applique les stats (calculees sur le train par _stats_par_entite) a
    n'importe quel jeu de films (train ou test). Un acteur jamais vu dans le
    train (ca arrive en test) recoit la moyenne globale du train, pas un 0 :
    on n'a pas d'info sur lui, autant rester neutre plutot que pessimiste."""
    liaisons = liaisons.merge(stats, on=colonne_nom, how="left")
    liaisons["popularite"] = liaisons["popularite"].fillna(0)
    liaisons["encodage_cible"] = liaisons["encodage_cible"].fillna(moyenne_cible_globale)

    par_film = liaisons.groupby("id_oeuvre").agg(
        nb=("popularite", "count"),
        pop_max=("popularite", "max"),
        cible_moyenne=("encodage_cible", "mean"),
    )
    par_film.columns = [f"{prefixe}_nb", f"{prefixe}_pop_max", f"{prefixe}_encodage_cible"]

    oeuvres = oeuvres.merge(par_film, on="id_oeuvre", how="left")
    oeuvres[f"{prefixe}_nb"] = oeuvres[f"{prefixe}_nb"].fillna(0)
    oeuvres[f"{prefixe}_pop_max"] = oeuvres[f"{prefixe}_pop_max"].fillna(0)
    oeuvres[f"{prefixe}_encodage_cible"] = oeuvres[f"{prefixe}_encodage_cible"].fillna(moyenne_cible_globale)
    return oeuvres


def _ajouter_genres(oeuvres: pd.DataFrame, genres: pd.DataFrame, colonnes_genre_train: list[str] | None):
    """One-hot des genres + nb_genres. Si colonnes_genre_train est fourni
    (cas du test), on reutilise exactement les memes colonnes que le train
    pour que X_train et X_test aient les memes features dans le meme ordre."""
    genres_par_film = pd.crosstab(genres["id_oeuvre"], genres["nom_genre"])
    genres_par_film.columns = [f"genre_{c}" for c in genres_par_film.columns]

    if colonnes_genre_train is not None:
        genres_par_film = genres_par_film.reindex(columns=colonnes_genre_train, fill_value=0)

    oeuvres = oeuvres.merge(genres_par_film, on="id_oeuvre", how="left")
    colonnes_genre = list(genres_par_film.columns)
    oeuvres[colonnes_genre] = oeuvres[colonnes_genre].fillna(0)
    oeuvres["nb_genres"] = oeuvres[colonnes_genre].sum(axis=1)
    return oeuvres, colonnes_genre


def construire_features(
    oeuvres_train: pd.DataFrame,
    oeuvres_test: pd.DataFrame,
    genres: pd.DataFrame,
    acteurs: pd.DataFrame,
    realisateurs: pd.DataFrame,
    productions: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Construit X_train/X_test a partir des tables brutes deja splittees.
    Toutes les stats (popularite, encodage cible, vocabulaire tf-idf) sont
    apprises sur le train puis appliquees telles quelles au test."""
    moyenne_cible_globale = np.log1p(oeuvres_train["entrees_premiere_semaine"]).mean()

    oeuvres_train, colonnes_genre = _ajouter_genres(oeuvres_train, genres, colonnes_genre_train=None)
    oeuvres_test, _ = _ajouter_genres(oeuvres_test, genres, colonnes_genre_train=colonnes_genre)

    for liaisons, colonne_nom, prefixe in [
        (acteurs, "nom_complet", "acteur"),
        (realisateurs, "nom_complet", "realisateur"),
        (productions, "nom_production", "production"),
        (genres, "nom_genre", "genre_cible"),
    ]:
        stats = _stats_par_entite(liaisons, colonne_nom, oeuvres_train, moyenne_cible_globale)
        oeuvres_train = _ajouter_features_entite(
            oeuvres_train, liaisons, colonne_nom, prefixe, stats, moyenne_cible_globale
        )
        oeuvres_test = _ajouter_features_entite(
            oeuvres_test, liaisons, colonne_nom, prefixe, stats, moyenne_cible_globale
        )

    # mots-cles : le vectoriseur tf-idf apprend son vocabulaire sur le train
    # uniquement, puis on l'applique tel quel au test (fit sur train, transform partout)
    # max_features baisse de 150 a 75 : sur le modele precedent, 78 des 150
    # colonnes motcle_ avaient une importance exactement nulle (jamais utilisees)
    for df in (oeuvres_train, oeuvres_test):
        df["mots_cles_texte"] = (
            df["mot_cle_1"].fillna("") + " " + df["mot_cle_2"].fillna("") + " " + df["mot_cle_3"].fillna("")
        )
    vectoriseur = TfidfVectorizer(max_features=75, ngram_range=(1, 2))
    tfidf_train = vectoriseur.fit_transform(oeuvres_train["mots_cles_texte"])
    tfidf_test = vectoriseur.transform(oeuvres_test["mots_cles_texte"])
    colonnes_motcle = [f"motcle_{m}" for m in vectoriseur.get_feature_names_out()]
    motcle_train_df = pd.DataFrame(tfidf_train.toarray(), columns=colonnes_motcle, index=oeuvres_train.index)
    motcle_test_df = pd.DataFrame(tfidf_test.toarray(), columns=colonnes_motcle, index=oeuvres_test.index)

    colonnes_a_garder = (
        ["annee_sortie", "note_tmdb", "note_imdb", "nb_genres"]
        + colonnes_genre
        + [
            "acteur_nb", "acteur_pop_max", "acteur_encodage_cible",
            "realisateur_nb", "realisateur_pop_max", "realisateur_encodage_cible",
            "production_nb", "production_pop_max", "production_encodage_cible",
            # genre_cible_nb retire : redondant avec nb_genres, importance nulle
            "genre_cible_pop_max", "genre_cible_encodage_cible",
        ]
    )

    X_train = pd.concat([oeuvres_train[colonnes_a_garder], motcle_train_df], axis=1)
    X_test = pd.concat([oeuvres_test[colonnes_a_garder], motcle_test_df], axis=1)
    y_train = oeuvres_train["entrees_premiere_semaine"]
    y_test = oeuvres_test["entrees_premiere_semaine"]

    return X_train, X_test, y_train, y_test


def charger_dataset_train_test(test_size: float = 0.2, random_state: int = 42):
    """Point d'entree principal : charge tout depuis postgres, fait le
    split, et renvoie X_train, X_test, y_train, y_test prets a l'emploi."""
    oeuvres, genres, acteurs, realisateurs, productions = charger_donnees_brutes()
    oeuvres_train, oeuvres_test = train_test_split(oeuvres, test_size=test_size, random_state=random_state)
    return construire_features(oeuvres_train, oeuvres_test, genres, acteurs, realisateurs, productions)
