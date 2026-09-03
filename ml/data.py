# Charge les films depuis postgres et construit les features. Le split
# train/test se fait avant de calculer l'encodage cible, sinon on a une
# fuite de donnees.
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split

from database.base import get_engine

# on garde que les films avec des entrees > 0 (les 0 sont surtout des
# vieux films avec des donnees jpbox pas fiables).
# pas de note_tmdb/note_imdb ici : ces notes sont construites apres la
# sortie du film, on ne les aura pas au moment de predire.
# langue_originale sert juste au sample_weight, ce n'est pas une feature.
REQUETE_OEUVRES = """
SELECT id_oeuvre, annee_sortie, langue_originale, nb_salles_predites, budget,
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

# memes requetes pour un seul film, sans le filtre sur les entrees
# (au moment de predire on ne les connait pas)
REQUETE_OEUVRE_PAR_ID = """
SELECT id_oeuvre, annee_sortie, nb_salles_predites, budget, mot_cle_1, mot_cle_2, mot_cle_3
FROM oeuvre WHERE id_oeuvre = %(id_oeuvre)s;
"""

REQUETE_GENRES_PAR_ID = """
SELECT go.id_oeuvre, g.nom_genre
FROM genre_oeuvre go JOIN genre g ON g.id_genre = go.id_genre
WHERE go.id_oeuvre = %(id_oeuvre)s;
"""

REQUETE_ACTEURS_PAR_ID = """
SELECT ao.id_oeuvre, a.prenom || ' ' || a.nom AS nom_complet
FROM acteur_oeuvre ao JOIN acteur a ON a.id_acteur = ao.id_acteur
WHERE ao.id_oeuvre = %(id_oeuvre)s;
"""

REQUETE_REALISATEURS_PAR_ID = """
SELECT ro.id_oeuvre, r.prenom || ' ' || r.nom AS nom_complet
FROM realisateur_oeuvre ro JOIN realisateur r ON r.id_realisateur = ro.id_realisateur
WHERE ro.id_oeuvre = %(id_oeuvre)s;
"""

REQUETE_PRODUCTIONS_PAR_ID = """
SELECT po.id_oeuvre, p.nom_societe AS nom_production
FROM production_oeuvre po JOIN production p ON p.id_production = po.id_production
WHERE po.id_oeuvre = %(id_oeuvre)s;
"""


def charger_donnees_brutes():
    """Charge les tables brutes depuis postgres, sans calcul sur la cible."""
    engine = get_engine()

    oeuvres = pd.read_sql(REQUETE_OEUVRES, engine)
    genres = pd.read_sql(REQUETE_GENRES, engine)
    acteurs = pd.read_sql(REQUETE_ACTEURS, engine)
    realisateurs = pd.read_sql(REQUETE_REALISATEURS, engine)
    productions = pd.read_sql(REQUETE_PRODUCTIONS, engine)

    # budget a 0 = budget inconnu, on le passe en NaN avant l'imputation
    oeuvres.loc[oeuvres["budget"] <= 0, "budget"] = np.nan

    # on garde les medianes, il en faudra les memes au moment de predire
    medianes = {}
    for colonne in ["annee_sortie", "nb_salles_predites", "budget"]:
        medianes[colonne] = oeuvres[colonne].median()
        oeuvres[colonne] = oeuvres[colonne].fillna(medianes[colonne])

    return oeuvres, genres, acteurs, realisateurs, productions, medianes


# lissage de l'encodage cible : quand quelqu'un a peu de films, on tire sa
# valeur vers la moyenne globale au lieu de croire son historique
POIDS_LISSAGE = 2

# a partir de 10 films un acteur/realisateur est considere comme un habitue
# (seuil choisi apres l'ANOVA, cf annexe data science)
SEUIL_HABITUE = 10


def _stats_par_entite(
    liaisons: pd.DataFrame,
    colonne_nom: str,
    oeuvres_train: pd.DataFrame,
    moyenne_cible_globale: float,
) -> pd.DataFrame:
    """Pour chaque acteur/realisateur/societe/genre, calcule sur le train
    seulement : sa popularite (nombre de films) et son encodage cible
    (moyenne en log des entrees de ses films, lissee)."""
    entrees_log_par_film = np.log1p(
        oeuvres_train.set_index("id_oeuvre")["entrees_premiere_semaine"]
    )
    liaisons_train = liaisons[liaisons["id_oeuvre"].isin(oeuvres_train["id_oeuvre"])].copy()
    liaisons_train["entrees_log"] = liaisons_train["id_oeuvre"].map(entrees_log_par_film)

    stats = liaisons_train.groupby(colonne_nom).agg(
        popularite=("id_oeuvre", "count"),
        moyenne_brute=("entrees_log", "mean"),
    )
    # avec 1 film on reste proche de la moyenne globale, avec 50 on suit
    # presque entierement sa moyenne a lui
    stats["encodage_cible"] = (
        stats["popularite"] * stats["moyenne_brute"] + POIDS_LISSAGE * moyenne_cible_globale
    ) / (stats["popularite"] + POIDS_LISSAGE)
    return stats[["popularite", "encodage_cible"]]


def _ajouter_features_entite(
    oeuvres: pd.DataFrame,
    liaisons: pd.DataFrame,
    colonne_nom: str,
    prefixe: str,
    stats: pd.DataFrame,
    moyenne_cible_globale: float,
) -> pd.DataFrame:
    """Applique les stats du train a un jeu de films (train ou test).
    Un acteur inconnu recoit la moyenne globale, pas 0."""
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
    oeuvres[f"{prefixe}_encodage_cible"] = oeuvres[f"{prefixe}_encodage_cible"].fillna(
        moyenne_cible_globale
    )
    return oeuvres


def _ajouter_genres(
    oeuvres: pd.DataFrame, genres: pd.DataFrame, colonnes_genre_train: list[str] | None
):
    """One-hot des genres + nb_genres. Sur le test on repasse les colonnes
    du train pour avoir les memes features dans le meme ordre."""
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
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, dict]:
    """Construit X_train/X_test a partir des tables deja splittees. Les
    stats et le vocabulaire tf-idf sont appris sur le train puis appliques
    au test. Renvoie aussi les artefacts a garder pour la prediction."""
    moyenne_cible_globale = np.log1p(oeuvres_train["entrees_premiere_semaine"]).mean()

    oeuvres_train, colonnes_genre = _ajouter_genres(
        oeuvres_train, genres, colonnes_genre_train=None
    )
    oeuvres_test, _ = _ajouter_genres(oeuvres_test, genres, colonnes_genre_train=colonnes_genre)

    stats_par_prefixe = {}
    for liaisons, colonne_nom, prefixe in [
        (acteurs, "nom_complet", "acteur"),
        (realisateurs, "nom_complet", "realisateur"),
        (productions, "nom_production", "production"),
        (genres, "nom_genre", "genre_cible"),
    ]:
        stats = _stats_par_entite(liaisons, colonne_nom, oeuvres_train, moyenne_cible_globale)
        stats_par_prefixe[prefixe] = stats
        oeuvres_train = _ajouter_features_entite(
            oeuvres_train, liaisons, colonne_nom, prefixe, stats, moyenne_cible_globale
        )
        oeuvres_test = _ajouter_features_entite(
            oeuvres_test, liaisons, colonne_nom, prefixe, stats, moyenne_cible_globale
        )

    # "habitue" = version 0/1 de pop_max : est-ce que le film a au moins un
    # acteur/realisateur present dans SEUIL_HABITUE films ou plus
    for df in (oeuvres_train, oeuvres_test):
        df["acteur_habitue"] = (df["acteur_pop_max"] >= SEUIL_HABITUE).astype(int)
        df["realisateur_habitue"] = (df["realisateur_pop_max"] >= SEUIL_HABITUE).astype(int)

    # mots-cles en tf-idf : fit sur le train, transform sur les deux.
    # 75 features, au dela la moitie des colonnes ne servaient a rien
    for df in (oeuvres_train, oeuvres_test):
        df["mots_cles_texte"] = (
            df["mot_cle_1"].fillna("")
            + " "
            + df["mot_cle_2"].fillna("")
            + " "
            + df["mot_cle_3"].fillna("")
        )
    vectoriseur = TfidfVectorizer(max_features=75, ngram_range=(1, 2))
    tfidf_train = vectoriseur.fit_transform(oeuvres_train["mots_cles_texte"])
    tfidf_test = vectoriseur.transform(oeuvres_test["mots_cles_texte"])
    colonnes_motcle = [f"motcle_{m}" for m in vectoriseur.get_feature_names_out()]
    motcle_train_df = pd.DataFrame(
        tfidf_train.toarray(), columns=colonnes_motcle, index=oeuvres_train.index
    )
    motcle_test_df = pd.DataFrame(
        tfidf_test.toarray(), columns=colonnes_motcle, index=oeuvres_test.index
    )

    colonnes_a_garder = (
        ["annee_sortie", "nb_salles_predites", "budget", "nb_genres"]
        + colonnes_genre
        + [
            "acteur_nb",
            "acteur_pop_max",
            "acteur_encodage_cible",
            "acteur_habitue",
            "realisateur_nb",
            "realisateur_pop_max",
            "realisateur_encodage_cible",
            "realisateur_habitue",
            "production_nb",
            "production_pop_max",
            "production_encodage_cible",
            # pas de genre_cible_nb, il fait doublon avec nb_genres
            "genre_cible_pop_max",
            "genre_cible_encodage_cible",
        ]
    )

    X_train = pd.concat([oeuvres_train[colonnes_a_garder], motcle_train_df], axis=1)
    X_test = pd.concat([oeuvres_test[colonnes_a_garder], motcle_test_df], axis=1)
    y_train = oeuvres_train["entrees_premiere_semaine"]
    y_test = oeuvres_test["entrees_premiere_semaine"]

    artefacts = {
        "moyenne_cible_globale": moyenne_cible_globale,
        "colonnes_genre": colonnes_genre,
        "stats_acteur": stats_par_prefixe["acteur"],
        "stats_realisateur": stats_par_prefixe["realisateur"],
        "stats_production": stats_par_prefixe["production"],
        "stats_genre_cible": stats_par_prefixe["genre_cible"],
        "vectoriseur_motcle": vectoriseur,
        "colonnes_finales": list(X_train.columns),
    }

    # langue du train, alignee sur l'index de X_train, pour le sample_weight
    artefacts["langue_originale_train"] = oeuvres_train["langue_originale"]

    return X_train, X_test, y_train, y_test, artefacts


def charger_dataset_train_test(test_size: float = 0.2, random_state: int = 42):
    """Charge la base, split, et renvoie X_train, X_test, y_train, y_test
    et les artefacts."""
    oeuvres, genres, acteurs, realisateurs, productions, medianes = charger_donnees_brutes()
    oeuvres_train, oeuvres_test = train_test_split(
        oeuvres, test_size=test_size, random_state=random_state
    )
    X_train, X_test, y_train, y_test, artefacts = construire_features(
        oeuvres_train, oeuvres_test, genres, acteurs, realisateurs, productions
    )
    artefacts["medianes"] = medianes
    return X_train, X_test, y_train, y_test, artefacts


def construire_features_pour_predire(id_oeuvre: int, artefacts: dict) -> pd.DataFrame:
    """Construit la ligne de features d'un seul film, en reutilisant les
    artefacts de l'entrainement (stats, vectoriseur, medianes, colonnes)."""
    engine = get_engine()
    params = {"id_oeuvre": id_oeuvre}

    oeuvre = pd.read_sql(REQUETE_OEUVRE_PAR_ID, engine, params=params)
    if oeuvre.empty:
        raise ValueError(f"aucun film avec id_oeuvre={id_oeuvre}")

    # meme traitement du budget que dans charger_donnees_brutes
    oeuvre.loc[oeuvre["budget"] <= 0, "budget"] = np.nan

    for colonne, mediane in artefacts["medianes"].items():
        oeuvre[colonne] = oeuvre[colonne].fillna(mediane).astype(float)

    genres = pd.read_sql(REQUETE_GENRES_PAR_ID, engine, params=params)
    acteurs = pd.read_sql(REQUETE_ACTEURS_PAR_ID, engine, params=params)
    realisateurs = pd.read_sql(REQUETE_REALISATEURS_PAR_ID, engine, params=params)
    productions = pd.read_sql(REQUETE_PRODUCTIONS_PAR_ID, engine, params=params)

    oeuvre, _ = _ajouter_genres(oeuvre, genres, colonnes_genre_train=artefacts["colonnes_genre"])

    for liaisons, colonne_nom, prefixe, cle_stats in [
        (acteurs, "nom_complet", "acteur", "stats_acteur"),
        (realisateurs, "nom_complet", "realisateur", "stats_realisateur"),
        (productions, "nom_production", "production", "stats_production"),
        (genres, "nom_genre", "genre_cible", "stats_genre_cible"),
    ]:
        oeuvre = _ajouter_features_entite(
            oeuvre,
            liaisons,
            colonne_nom,
            prefixe,
            artefacts[cle_stats],
            artefacts["moyenne_cible_globale"],
        )

    oeuvre["acteur_habitue"] = (oeuvre["acteur_pop_max"] >= SEUIL_HABITUE).astype(int)
    oeuvre["realisateur_habitue"] = (oeuvre["realisateur_pop_max"] >= SEUIL_HABITUE).astype(int)

    oeuvre["mots_cles_texte"] = (
        oeuvre["mot_cle_1"].fillna("")
        + " "
        + oeuvre["mot_cle_2"].fillna("")
        + " "
        + oeuvre["mot_cle_3"].fillna("")
    )
    tfidf = artefacts["vectoriseur_motcle"].transform(oeuvre["mots_cles_texte"])
    colonnes_motcle = [
        f"motcle_{m}" for m in artefacts["vectoriseur_motcle"].get_feature_names_out()
    ]
    motcle_df = pd.DataFrame(tfidf.toarray(), columns=colonnes_motcle, index=oeuvre.index)

    X = pd.concat([oeuvre, motcle_df], axis=1)
    # on remet les colonnes dans l'ordre de l'entrainement
    return X[artefacts["colonnes_finales"]]
