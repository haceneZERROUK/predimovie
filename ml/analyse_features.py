# Regroupe les features par famille pour les graphiques du rapport.
#
# Le modele a 111 colonnes, dont 75 mots-cles tf-idf et 19 genres one-hot :
# un top 15 feature par feature ne montre que des miettes eparpillees. Ici
# on somme l'importance de chaque famille pour voir ce qui compte vraiment.
#
# Cote correlations, on ne somme rien : additionner des coefficients de
# Pearson n'a pas de sens. Les variables continues ont leur Pearson, et les
# familles categorielles (genre, acteur...) passent par un omega carre, qui
# dit la meme chose (part de variance expliquee) mais pour un groupe.
import matplotlib

matplotlib.use("Agg")

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ml.data import charger_donnees_brutes

DOSSIER_IMAGES = "explication/data_rapport/images"
COULEUR_PRINCIPALE = "#2563eb"
COULEUR_GROUPE = "#f59e0b"

plt.rcParams["font.size"] = 11
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False

# ordre important : genre_cible_ doit passer avant genre_, sinon les 2
# colonnes d'encodage cible se retrouvent comptees avec les 19 one-hot
FAMILLES = [
    ("genre_cible_", "Genre (encodage cible)"),
    ("motcle_", "Mots-cles (tf-idf)"),
    ("genre_", "Genres (one-hot)"),
    ("acteur_", "Acteurs"),
    ("realisateur_", "Realisateurs"),
    ("production_", "Societes de production"),
]


def famille_de(colonne: str) -> str:
    """Renvoie le nom de famille d'une colonne, ou la colonne elle-meme
    quand elle ne fait partie d'aucun groupe (budget, annee_sortie...)."""
    for prefixe, nom in FAMILLES:
        if colonne.startswith(prefixe):
            return nom
    return colonne


def importances_groupees(chemin_modele: str, chemin_artefacts: str) -> pd.DataFrame:
    """Somme l'importance du modele champion par famille de features.
    Additionner est legitime ici : les importances d'un modele a arbres se
    partagent la reduction d'erreur totale, elles s'ajoutent."""
    modele = joblib.load(chemin_modele)
    artefacts = joblib.load(chemin_artefacts)
    colonnes = artefacts["colonnes_finales"]

    brut = pd.DataFrame(
        {"feature": colonnes, "importance": modele.feature_importances_[: len(colonnes)]}
    )
    brut["famille"] = brut["feature"].map(famille_de)

    groupe = (
        brut.groupby("famille")
        .agg(importance=("importance", "sum"), nb_colonnes=("feature", "count"))
        .sort_values("importance", ascending=False)
        .reset_index()
    )
    groupe["part"] = 100 * groupe["importance"] / groupe["importance"].sum()
    return groupe


def graphique_importances_groupees(groupe: pd.DataFrame):
    tri = groupe.sort_values("importance")
    etiquettes = [
        f"{f}  ({n} col.)" if n > 1 else f
        for f, n in zip(tri["famille"], tri["nb_colonnes"], strict=True)
    ]
    couleurs = [COULEUR_GROUPE if n > 1 else COULEUR_PRINCIPALE for n in tri["nb_colonnes"]]

    fig, ax = plt.subplots(figsize=(10, 6))
    barres = ax.barh(etiquettes, tri["part"], color=couleurs)
    ax.bar_label(barres, fmt="%.1f%%", padding=3, fontsize=9)
    ax.set_xlabel("part de l'importance totale (%)")
    ax.set_xlim(0, tri["part"].max() * 1.18)
    ax.set_title("Importance des features, regroupee par famille\n(modele champion)")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/importance_features_groupees.png", dpi=150)
    plt.close(fig)


def omega_carre(valeurs: pd.Series, groupes: pd.Series) -> float:
    """Part de la variance de `valeurs` expliquee par le groupe, corrigee du
    nombre de groupes.

    On n'utilise pas l'eta carre brut : avec 4597 realisateurs pour 10 000
    films, la plupart des groupes ne contiennent qu'un seul film, et l'eta
    carre monte alors mecaniquement vers 1 sans qu'il y ait le moindre
    signal. L'omega carre retranche ce que le hasard explique deja, donc il
    reste comparable a un r2 de Pearson."""
    donnees = pd.DataFrame({"y": valeurs, "g": groupes}).dropna()
    n, k = len(donnees), donnees["g"].nunique()
    if k < 2 or n - k < 1:
        return float("nan")
    moyenne = donnees["y"].mean()
    sc_totale = ((donnees["y"] - moyenne) ** 2).sum()
    if sc_totale == 0:
        return float("nan")
    sc_inter = sum(
        len(sous) * (sous["y"].mean() - moyenne) ** 2 for _, sous in donnees.groupby("g")
    )
    carre_moyen_intra = (sc_totale - sc_inter) / (n - k)
    omega = (sc_inter - (k - 1) * carre_moyen_intra) / (sc_totale + carre_moyen_intra)
    return max(omega, 0.0)


def correlations_groupees() -> pd.DataFrame:
    """Lien entre chaque variable brute et les entrees premiere semaine.
    Pearson (au carre) pour les variables continues, omega carre pour les
    familles categorielles : les deux se lisent comme une part de variance
    expliquee, donc sur la meme echelle."""
    oeuvres, genres, acteurs, realisateurs, productions = charger_donnees_brutes()[:5]
    cible = np.log1p(oeuvres.set_index("id_oeuvre")["entrees_premiere_semaine"])

    lignes = []
    for colonne in ["budget", "nb_salles_predites", "annee_sortie"]:
        serie = oeuvres.set_index("id_oeuvre")[colonne]
        valide = serie.notna() & cible.notna()
        r = serie[valide].corr(cible[valide])
        lignes.append(
            {"variable": colonne, "mesure": "Pearson r2", "score": r**2, "nb_modalites": 1}
        )

    # pour une famille, on prend la modalite principale de chaque film (la
    # plus frequente dans la base) : un film a plusieurs genres/acteurs, il
    # faut bien un seul groupe par film pour calculer un omega carre
    for liaisons, colonne_nom, nom_famille in [
        (genres, "nom_genre", "Genres"),
        (acteurs, "nom_complet", "Acteurs"),
        (realisateurs, "nom_complet", "Realisateurs"),
        (productions, "nom_production", "Societes de production"),
    ]:
        frequences = liaisons[colonne_nom].value_counts()
        liaisons = liaisons.copy()
        liaisons["freq"] = liaisons[colonne_nom].map(frequences)
        principale = (
            liaisons.sort_values("freq", ascending=False)
            .drop_duplicates("id_oeuvre")
            .set_index("id_oeuvre")[colonne_nom]
        )
        commun = cible.index.intersection(principale.index)
        lignes.append(
            {
                "variable": nom_famille,
                "mesure": "omega2 (ANOVA)",
                "score": omega_carre(cible.loc[commun], principale.loc[commun]),
                "nb_modalites": principale.loc[commun].nunique(),
            }
        )

    return pd.DataFrame(lignes).sort_values("score", ascending=False).reset_index(drop=True)


def graphique_correlations_groupees(correlations: pd.DataFrame):
    tri = correlations.dropna(subset=["score"]).sort_values("score")
    etiquettes = [
        f"{v}  ({n} modalites)" if n > 1 else v
        for v, n in zip(tri["variable"], tri["nb_modalites"], strict=True)
    ]
    couleurs = [COULEUR_GROUPE if n > 1 else COULEUR_PRINCIPALE for n in tri["nb_modalites"]]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    barres = ax.barh(etiquettes, tri["score"], color=couleurs)
    ax.bar_label(barres, fmt="%.3f", padding=3, fontsize=9)
    ax.set_xlabel("part de la variance des entrees expliquee (log)")
    ax.set_xlim(0, max(tri["score"].max() * 1.18, 0.05))
    ax.set_title(
        "Lien entre les variables brutes et les entrees\n"
        "Pearson r2 pour les continues, omega2 (ANOVA corrigee) pour les familles"
    )
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/correlations_groupees.png", dpi=150)
    plt.close(fig)


def main():
    groupe = importances_groupees("ml/modele_champion.joblib", "ml/artefacts_features.joblib")
    print("\n=== IMPORTANCE PAR FAMILLE ===")
    print(groupe.to_string(index=False))
    graphique_importances_groupees(groupe)

    correlations = correlations_groupees()
    print("\n=== LIEN AVEC LES ENTREES (donnees brutes) ===")
    print(correlations.to_string(index=False))
    graphique_correlations_groupees(correlations)
    print(f"\ngraphiques ecrits dans {DOSSIER_IMAGES}/")


if __name__ == "__main__":
    main()
