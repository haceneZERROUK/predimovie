# Petit modele a part qui predit le nombre de salles en 1ere semaine, a
# partir du budget, du genre, du casting et du mois de sortie. Le vrai
# nombre de salles n'est connu qu'apres la sortie, donc on l'estime ici et
# la prediction devient une feature du modele principal.
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

from database.base import get_engine

REQUETE_OEUVRES = """
SELECT id_oeuvre, annee_sortie, date_sortie, budget, nb_salles_semaine1
FROM oeuvre;
"""

REQUETE_GENRES = """
SELECT go.id_oeuvre, g.nom_genre
FROM genre_oeuvre go JOIN genre g ON g.id_genre = go.id_genre;
"""

REQUETE_COMPTAGES = """
SELECT id_oeuvre, count(*) AS nb FROM acteur_oeuvre GROUP BY id_oeuvre;
"""

REQUETE_COMPTAGES_REALISATEUR = """
SELECT id_oeuvre, count(*) AS nb FROM realisateur_oeuvre GROUP BY id_oeuvre;
"""

REQUETE_COMPTAGES_PRODUCTION = """
SELECT id_oeuvre, count(*) AS nb FROM production_oeuvre GROUP BY id_oeuvre;
"""


def _construire_features(oeuvres: pd.DataFrame, genres: pd.DataFrame, colonnes_genre=None):
    """Features simples : budget, mois de sortie, genres en one-hot et
    nombre d'acteurs/realisateurs/societes. Pas d'encodage cible ici."""
    oeuvres = oeuvres.copy()
    oeuvres["mois_sortie"] = pd.to_datetime(oeuvres["date_sortie"]).dt.month

    genres_par_film = pd.crosstab(genres["id_oeuvre"], genres["nom_genre"])
    genres_par_film.columns = [f"genre_{c}" for c in genres_par_film.columns]
    if colonnes_genre is not None:
        genres_par_film = genres_par_film.reindex(columns=colonnes_genre, fill_value=0)
    oeuvres = oeuvres.merge(genres_par_film, on="id_oeuvre", how="left")
    colonnes_genre = list(genres_par_film.columns)
    oeuvres[colonnes_genre] = oeuvres[colonnes_genre].fillna(0)

    return oeuvres, colonnes_genre


def charger_donnees():
    """Charge et fusionne les donnees de tous les films, pas seulement ceux
    dont on connait deja nb_salles_semaine1."""
    engine = get_engine()
    oeuvres = pd.read_sql(REQUETE_OEUVRES, engine)
    genres = pd.read_sql(REQUETE_GENRES, engine)
    acteurs = pd.read_sql(REQUETE_COMPTAGES, engine).rename(columns={"nb": "acteur_nb"})
    realisateurs = pd.read_sql(REQUETE_COMPTAGES_REALISATEUR, engine).rename(
        columns={"nb": "realisateur_nb"}
    )
    productions = pd.read_sql(REQUETE_COMPTAGES_PRODUCTION, engine).rename(
        columns={"nb": "production_nb"}
    )

    oeuvres = oeuvres.merge(acteurs, on="id_oeuvre", how="left")
    oeuvres = oeuvres.merge(realisateurs, on="id_oeuvre", how="left")
    oeuvres = oeuvres.merge(productions, on="id_oeuvre", how="left")
    for colonne in ["acteur_nb", "realisateur_nb", "production_nb"]:
        oeuvres[colonne] = oeuvres[colonne].fillna(0)

    return oeuvres, genres


COLONNES_NUMERIQUES = [
    "annee_sortie",
    "mois_sortie",
    "budget",
    "acteur_nb",
    "realisateur_nb",
    "production_nb",
]


def entrainer_et_predire_pour_tous():
    """Entraine sur les films dont on connait nb_salles_semaine1, puis
    predit pour tous les films."""
    oeuvres, genres = charger_donnees()
    oeuvres, colonnes_genre = _construire_features(oeuvres, genres)

    medianes = {}
    for colonne in COLONNES_NUMERIQUES:
        medianes[colonne] = oeuvres[colonne].median()
        oeuvres[colonne] = oeuvres[colonne].fillna(medianes[colonne])

    colonnes_finales = COLONNES_NUMERIQUES + colonnes_genre
    X = oeuvres[colonnes_finales]

    entrainement = oeuvres[oeuvres["nb_salles_semaine1"].notna()]
    X_entrainement = X.loc[entrainement.index]
    y_entrainement = np.log1p(entrainement["nb_salles_semaine1"])

    print(f"{len(X_entrainement)} films avec nb_salles connu, {len(colonnes_finales)} features")

    modele = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, random_state=42)
    modele.fit(X_entrainement, y_entrainement)

    predictions_log = modele.predict(X)
    predictions = np.expm1(predictions_log).clip(min=0)
    oeuvres["nb_salles_predites"] = predictions

    return oeuvres[["id_oeuvre", "nb_salles_predites"]], modele


def sauvegarder_predictions_en_base(predictions: pd.DataFrame):
    """Ecrit nb_salles_predites en base, par paquets de 1000."""
    from database.base import SessionLocal
    from database.models import Oeuvre

    session = SessionLocal()
    maj = 0
    for _, ligne in predictions.iterrows():
        session.query(Oeuvre).filter_by(id_oeuvre=int(ligne["id_oeuvre"])).update(
            {"nb_salles_predites": float(ligne["nb_salles_predites"])}
        )
        maj += 1
        if maj % 1000 == 0:
            session.commit()
    session.commit()
    session.close()
    print(f"{maj} films mis a jour avec nb_salles_predites")


if __name__ == "__main__":
    predictions, _modele = entrainer_et_predire_pour_tous()
    sauvegarder_predictions_en_base(predictions)
