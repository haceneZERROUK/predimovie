# Script a part du pipeline : sort les graphiques du rapport a partir des
# runs mlflow.
import matplotlib

matplotlib.use("Agg")  # pas d'ecran, on sauvegarde juste des png

import joblib
import matplotlib.pyplot as plt
import mlflow
import numpy as np
import pandas as pd

from ml.data import charger_dataset_train_test

DOSSIER_IMAGES = "explication/data_rapport/images"
COULEUR_PRINCIPALE = "#2563eb"
COULEUR_CHAMPION = "#16a34a"

plt.rcParams["font.size"] = 11
plt.rcParams["axes.spines.top"] = False
plt.rcParams["axes.spines.right"] = False


def recuperer_runs():
    client = mlflow.MlflowClient()
    exp = client.get_experiment_by_name("predimovie-entrees-premiere-semaine")
    runs = client.search_runs(exp.experiment_id, order_by=["metrics.rmse ASC"])
    lignes = []
    for r in runs:
        lignes.append(
            {
                "modele": r.data.tags.get("mlflow.runName"),
                "rmse": r.data.metrics["rmse"],
                "mae": r.data.metrics["mae"],
                "r2": r.data.metrics["r2"],
                "rmse_gros_films": r.data.metrics.get("rmse_gros_films"),
                "rmse_petits_films": r.data.metrics.get("rmse_petits_films"),
                "duree_secondes": r.data.metrics["duree_secondes"],
                "run_id": r.info.run_id,
            }
        )
    return client, pd.DataFrame(lignes)


def graphique_comparaison(client, resultats: pd.DataFrame):
    """3 barres cote a cote : rmse, mae, r2 pour chaque modele."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    couleurs = [COULEUR_CHAMPION if i == 0 else COULEUR_PRINCIPALE for i in range(len(resultats))]

    for ax, colonne, titre in zip(
        axes,
        ["rmse", "mae", "r2"],
        ["RMSE (plus bas = mieux)", "MAE (plus bas = mieux)", "R² (plus haut = mieux)"],
        strict=True,
    ):
        ax.barh(resultats["modele"], resultats[colonne], color=couleurs)
        ax.set_title(titre)
        ax.invert_yaxis()

    fig.suptitle("Comparaison des 7 modeles testes", fontsize=14, fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/comparaison_modeles.png", dpi=150)
    plt.close(fig)


def graphique_duree(resultats: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))
    tri = resultats.sort_values("duree_secondes")
    ax.barh(tri["modele"], tri["duree_secondes"] / 60, color=COULEUR_PRINCIPALE)
    ax.set_xlabel("minutes")
    ax.set_title("Temps de la recherche d'hyperparametres par modele")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/duree_entrainement.png", dpi=150)
    plt.close(fig)


def graphique_importance_champion(client, run_id_champion: str, nom_champion: str):
    chemin_local = mlflow.artifacts.download_artifacts(
        run_id=run_id_champion, artifact_path=f"importance_{nom_champion}.csv"
    )
    importances_completes = pd.read_csv(chemin_local)
    importances = importances_completes.head(15).sort_values("importance")

    fig, ax = plt.subplots(figsize=(9, 6))
    couleurs = [
        "#f59e0b" if f.startswith("motcle_") else COULEUR_CHAMPION for f in importances["feature"]
    ]
    ax.barh(importances["feature"], importances["importance"], color=couleurs)
    ax.set_title(f"15 features les plus importantes\n(modele champion : {nom_champion})")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/importance_features_champion.png", dpi=150)
    plt.close(fig)

    return importances_completes


def graphique_importance_mots_cles(importances_completes: pd.DataFrame):
    """Compare le poids des features motcle_ au reste des features."""
    motcles = importances_completes[importances_completes["feature"].str.startswith("motcle_")]
    autres = importances_completes[~importances_completes["feature"].str.startswith("motcle_")]

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    part_motcles = motcles["importance"].sum()
    part_autres = autres["importance"].sum()
    axes[0].pie(
        [part_motcles, part_autres],
        labels=[
            f"mots-cles\n({len(motcles)} features)",
            f"autres features\n({len(autres)} features)",
        ],
        colors=["#f59e0b", COULEUR_PRINCIPALE],
        autopct="%1.0f%%",
    )
    axes[0].set_title("Part des mots-cles dans\nl'importance totale (top 30)")

    top_motcles = motcles.sort_values("importance", ascending=True).tail(10)
    axes[1].barh(top_motcles["feature"], top_motcles["importance"], color="#f59e0b")
    axes[1].set_title("Les 10 mots-cles les plus utiles")

    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/importance_mots_cles.png", dpi=150)
    plt.close(fig)


def graphique_gros_vs_petits(resultats: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))
    tri = resultats.sort_values("rmse")
    largeur = 0.35
    positions = range(len(tri))
    ax.barh(
        [p + largeur / 2 for p in positions],
        tri["rmse_gros_films"],
        height=largeur,
        label="gros films (>500k entrees)",
        color="#dc2626",
    )
    ax.barh(
        [p - largeur / 2 for p in positions],
        tri["rmse_petits_films"],
        height=largeur,
        label="petits films",
        color=COULEUR_PRINCIPALE,
    )
    ax.set_yticks(list(positions))
    ax.set_yticklabels(tri["modele"])
    ax.invert_yaxis()
    ax.set_title("RMSE separe : gros films vs petits films")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/gros_vs_petits_films.png", dpi=150)
    plt.close(fig)


def graphique_predictions_vs_reel(run_id_champion: str, nom_champion: str):
    """Recharge le champion et trace ses predictions contre les vraies
    entrees du jeu de test."""
    chemin_modele = mlflow.artifacts.download_artifacts(
        run_id=run_id_champion, artifact_path=f"modele_{nom_champion}.joblib"
    )
    modele = joblib.load(chemin_modele)

    _, X_test, _, y_test, _ = charger_dataset_train_test()
    predictions = np.expm1(modele.predict(X_test)).clip(min=0)

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.scatter(y_test, predictions, alpha=0.3, s=15, color=COULEUR_PRINCIPALE)
    limite = max(y_test.max(), predictions.max())
    ax.plot([0, limite], [0, limite], color="#dc2626", linestyle="--", label="prediction parfaite")
    ax.set_xlabel("entrees reelles")
    ax.set_ylabel("entrees predites")
    ax.set_title("Predictions vs realite (modele champion, jeu de test)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/predictions_vs_reel.png", dpi=150)
    plt.close(fig)

    return y_test, predictions


def graphique_distribution_cible():
    _, _, y_train, y_test, _ = charger_dataset_train_test()
    y = pd.concat([y_train, y_test])
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    axes[0].hist(y, bins=60, color=COULEUR_PRINCIPALE)
    axes[0].set_title("Entrees premiere semaine (echelle normale)")
    axes[0].set_xlabel("entrees")

    axes[1].hist(np.log1p(y), bins=60, color=COULEUR_PRINCIPALE)
    axes[1].set_title("Meme donnee apres log1p\n(ce que le modele voit vraiment)")
    axes[1].set_xlabel("log(1 + entrees)")

    fig.suptitle("Pourquoi on entraine sur le log des entrees", fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/distribution_cible.png", dpi=150)
    plt.close(fig)


# chiffres recopies a la main depuis les runs mlflow. Pour V2 on met la
# version corrigee, le premier essai s'etait effondre (R2 0.072).
EVOLUTION_ITERATIONS = pd.DataFrame(
    [
        {
            "version": "V1\n(retrait notes\nleak, lissage)",
            "rmse": 254654,
            "r2": 0.264,
            "statut": "ok",
        },
        {
            "version": "V2\n(ponderation\ncategorie)",
            "rmse": 280407,
            "r2": 0.205,
            "statut": "abandonnee",
        },
        {"version": "V3\n(sous-modele\nsalles)", "rmse": 262907, "r2": 0.325, "statut": "ok"},
        {"version": "V4\n(budget)", "rmse": 262606, "r2": 0.327, "statut": "ok"},
        {
            "version": "V5\n(acteur/realisateur\nhabitue)",
            "rmse": 262559,
            "r2": 0.327,
            "statut": "ok",
        },
    ]
)


def graphique_evolution():
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    couleurs = [
        "#dc2626" if statut == "abandonnee" else COULEUR_PRINCIPALE
        for statut in EVOLUTION_ITERATIONS["statut"]
    ]
    couleurs[-1] = COULEUR_CHAMPION  # V5 = modele champion actuel

    axes[0].bar(EVOLUTION_ITERATIONS["version"], EVOLUTION_ITERATIONS["rmse"], color=couleurs)
    axes[0].set_title("RMSE du meilleur modele\npar iteration")

    axes[1].bar(EVOLUTION_ITERATIONS["version"], EVOLUTION_ITERATIONS["r2"], color=couleurs)
    axes[1].set_title("R² du meilleur modele\npar iteration")

    fig.suptitle("Evolution sur les iterations V1 a V5 (CatBoost)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(f"{DOSSIER_IMAGES}/evolution_iterations.png", dpi=150)
    plt.close(fig)


# run_id note en dur : le run avec le plus petit RMSE n'est pas le
# champion, le dataset a grossi entre V1 et V5 donc les RMSE ne sont pas
# comparables. Le champion c'est le dernier run logue.
RUN_ID_CHAMPION_ACTUEL = "3a7acbaf5b3b4fc38149991b107546ba"  # catboost, V5


def main():
    client, resultats = recuperer_runs()
    print(resultats)

    graphique_comparaison(client, resultats)
    graphique_duree(resultats)
    graphique_gros_vs_petits(resultats)
    graphique_evolution()

    run_id_champion = RUN_ID_CHAMPION_ACTUEL
    nom_champion = "catboost"
    importances_completes = graphique_importance_champion(client, run_id_champion, nom_champion)
    graphique_importance_mots_cles(importances_completes)
    y_test, predictions = graphique_predictions_vs_reel(run_id_champion, nom_champion)
    graphique_distribution_cible()

    print("\ngraphiques sauvegardes dans", DOSSIER_IMAGES)


if __name__ == "__main__":
    main()
