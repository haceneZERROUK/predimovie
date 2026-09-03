# Entraine les modeles qui predisent entrees_premiere_semaine, avec une
# recherche d'hyperparametres sur chacun, et logue tout dans mlflow.
import json
import time
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import RandomizedSearchCV
from xgboost import XGBRegressor

from ml.data import charger_dataset_train_test

CV = 5
N_ITER_RANDOM_SEARCH = 40

# au-dessus de ce seuil on parle de "gros film", pour calculer un rmse
# separe sur les gros et sur les petits
SEUIL_GROS_FILM = 500_000

CHEMIN_CHAMPION = "ml/modele_champion.joblib"
CHEMIN_METRIQUES_CHAMPION = "ml/modele_champion_metrics.json"

# on ne remplace le champion que si le rmse ne se degrade pas de plus de 5%
SEUIL_DEGRADATION_RMSE = 0.05


def doit_remplacer_champion(
    nouveau_rmse: float, ancien_rmse: float | None, seuil: float = SEUIL_DEGRADATION_RMSE
) -> bool:
    """Dit si le nouveau modele doit remplacer le champion. Toujours oui
    s'il n'y a pas encore de champion."""
    if ancien_rmse is None:
        return True
    return (nouveau_rmse - ancien_rmse) / ancien_rmse <= seuil


# on ne garde que xgboost et catboost, les autres (ridge, lasso, random
# forest, gradient boosting) finissaient toujours derriere
MODELES = {
    "xgboost": {
        "estimateur": XGBRegressor(random_state=42),
        "grille": {
            "n_estimators": [100, 200, 300, 500],
            "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2],
            "max_depth": [3, 4, 5, 6, 8],
            "subsample": [0.6, 0.8, 1.0],
            "colsample_bytree": [0.6, 0.8, 1.0],
            "reg_alpha": [0, 0.1, 1],
            "reg_lambda": [1, 5, 10],
        },
    },
    "catboost": {
        # thread_count=1, c'est RandomizedSearchCV qui gere le parallelisme
        "estimateur": CatBoostRegressor(random_state=42, thread_count=1, verbose=0),
        "grille": {
            "iterations": [200, 400, 600, 900],
            "learning_rate": [0.01, 0.03, 0.05, 0.1, 0.2],
            "depth": [4, 6, 8, 10],
            "l2_leaf_reg": [1, 3, 5, 10],
            "subsample": [0.6, 0.8, 1.0],
        },
    },
}


def _importance_features(modele, colonnes: list[str], X_test, y_test_log) -> pd.DataFrame:
    """Importance des features selon le type de modele : arbres, modele
    lineaire, ou permutation_importance si le modele n'expose rien."""
    if hasattr(modele, "feature_importances_"):
        valeurs = modele.feature_importances_
    elif hasattr(modele, "coef_"):
        valeurs = np.abs(modele.coef_)
    else:
        resultat = permutation_importance(
            modele, X_test, y_test_log, n_repeats=5, random_state=42, n_jobs=-1
        )
        valeurs = resultat.importances_mean
    return (
        pd.DataFrame({"feature": colonnes, "importance": valeurs})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def entrainer_un_modele(
    nom_modele: str, config: dict, X_train, X_test, y_train_log, y_test, poids_train
):
    """Lance la recherche d'hyperparametres, logue dans mlflow et renvoie
    les metriques du meilleur essai."""
    print(f"\n=== {nom_modele} ===")
    debut = time.time()

    recherche = RandomizedSearchCV(
        config["estimateur"],
        config["grille"],
        n_iter=N_ITER_RANDOM_SEARCH,
        cv=CV,
        scoring="neg_root_mean_squared_error",
        n_jobs=-1,
        random_state=42,
    )

    # on entraine sur log1p(entrees) : la distribution est tres etalee
    recherche.fit(X_train, np.log1p(y_train_log), sample_weight=poids_train)

    # et on repasse en vraies entrees pour evaluer
    predictions_log = recherche.predict(X_test)
    predictions = np.expm1(predictions_log).clip(min=0)

    rmse = mean_squared_error(y_test, predictions) ** 0.5
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # rmse separe sur les gros et les petits films
    masque_gros = y_test >= SEUIL_GROS_FILM
    rmse_gros = mean_squared_error(y_test[masque_gros], predictions[masque_gros]) ** 0.5
    rmse_petits = mean_squared_error(y_test[~masque_gros], predictions[~masque_gros]) ** 0.5

    duree = time.time() - debut
    print(f"  meilleurs parametres : {recherche.best_params_}")
    print(f"  rmse={rmse:.0f}  mae={mae:.0f}  r2={r2:.3f}  ({duree:.0f}s)")
    print(
        f"  rmse gros films (>{SEUIL_GROS_FILM:,}, n={masque_gros.sum()}): {rmse_gros:.0f}"
        f"   rmse petits films (n={(~masque_gros).sum()}): {rmse_petits:.0f}"
    )

    with mlflow.start_run(run_name=nom_modele):
        # note de version, pour se souvenir de ce qui a change quand on
        # relit les metriques dans mlflow plus tard
        mlflow.set_tag(
            "motif_reentrainement",
            "V6 : retire note_tmdb et note_imdb (fuite temporelle, ces notes "
            "sont ecrasees a leur valeur actuelle a chaque scraping) ; "
            "POIDS_LISSAGE passe de 8 a 2 ; sample_weight = entrees brutes, "
            "sans ponderation par categorie (essayee en V7, abandonnee). "
            "Ajoute aussi budget en feature directe, acteur_habitue et "
            "realisateur_habitue.",
        )
        mlflow.log_param("modele", nom_modele)
        mlflow.log_params(recherche.best_params_)
        mlflow.log_metric("rmse", rmse)
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2", r2)
        mlflow.log_metric("rmse_gros_films", rmse_gros)
        mlflow.log_metric("rmse_petits_films", rmse_petits)
        mlflow.log_metric("duree_secondes", duree)

        importances = _importance_features(
            recherche.best_estimator_, list(X_train.columns), X_test, np.log1p(y_test)
        )
        chemin_csv = f"/tmp/importance_{nom_modele}.csv"
        importances.head(30).to_csv(chemin_csv, index=False)
        mlflow.log_artifact(chemin_csv)

        # joblib + log_artifact plutot que mlflow.sklearn.log_model, qui
        # refuse de sauvegarder xgboost
        chemin_modele = f"/tmp/modele_{nom_modele}.joblib"
        joblib.dump(recherche.best_estimator_, chemin_modele)
        mlflow.log_artifact(chemin_modele)
        run_id = mlflow.active_run().info.run_id

    return {
        "nom_modele": nom_modele,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "rmse_gros_films": rmse_gros,
        "rmse_petits_films": rmse_petits,
        "run_id": run_id,
        "modele": recherche.best_estimator_,
        "importances": importances,
    }


def main():
    # a laisser dans main() : au niveau module, importer ml.train suffisait
    # a initialiser mlflow et le backend mettait trop longtemps a demarrer
    mlflow.set_experiment("predimovie-entrees-premiere-semaine")

    print("chargement des donnees depuis postgres...")
    X_train, X_test, y_train, y_test, artefacts = charger_dataset_train_test()
    print(f"{len(X_train) + len(X_test)} films, {X_train.shape[1]} features")

    # poids = entrees brutes : un gros film pese plus lourd dans la
    # fonction de cout qu'un petit
    poids_train = y_train.to_numpy()

    resultats = []
    for nom_modele, config in MODELES.items():
        resultat = entrainer_un_modele(
            nom_modele, config, X_train, X_test, y_train, y_test, poids_train
        )
        resultats.append(resultat)

    resultats.sort(key=lambda r: r["rmse"])

    print("\n\n=== CLASSEMENT FINAL (du meilleur au moins bon) ===")
    for r in resultats:
        print(
            f"  {r['nom_modele']:25s} rmse={r['rmse']:>8.0f}"
            f"  mae={r['mae']:>8.0f}  r2={r['r2']:.3f}"
            f"  rmse_gros={r['rmse_gros_films']:>8.0f}"
            f"  rmse_petits={r['rmse_petits_films']:>8.0f}"
        )

    meilleur = resultats[0]
    print(f"\nmeilleur modele : {meilleur['nom_modele']} (rmse={meilleur['rmse']:.0f})")
    print("features les plus importantes pour ce modele :")
    print(meilleur["importances"].head(15).to_string(index=False))

    ancien_rmse = None
    if Path(CHEMIN_METRIQUES_CHAMPION).exists():
        ancien_rmse = json.loads(Path(CHEMIN_METRIQUES_CHAMPION).read_text())["rmse"]

    if not doit_remplacer_champion(meilleur["rmse"], ancien_rmse):
        degradation = (meilleur["rmse"] - ancien_rmse) / ancien_rmse
        print(
            f"\nCHAMPION NON REMPLACE : rmse={meilleur['rmse']:.0f} degrade le champion "
            f"en place (rmse={ancien_rmse:.0f}) de {degradation:.1%}, au-dela du seuil "
            f"tolere ({SEUIL_DEGRADATION_RMSE:.0%}). Le run reste consultable dans mlflow "
            "(run_id ci-dessus) mais ml/modele_champion.joblib n'est pas touche."
        )
        return

    joblib.dump(meilleur["modele"], CHEMIN_CHAMPION)
    # les artefacts (vectoriseur, stats d'encodage, medianes...) servent a
    # l'API pour refaire les memes features au moment de predire
    joblib.dump(artefacts, "ml/artefacts_features.joblib")
    Path(CHEMIN_METRIQUES_CHAMPION).write_text(
        json.dumps(
            {
                "nom_modele": meilleur["nom_modele"],
                "rmse": meilleur["rmse"],
                "mae": meilleur["mae"],
                "r2": meilleur["r2"],
                "run_id": meilleur["run_id"],
            },
            indent=2,
        )
    )
    print(f"\nmodele champion sauvegarde dans {CHEMIN_CHAMPION}")
    print("artefacts de features sauvegardes dans ml/artefacts_features.joblib")


if __name__ == "__main__":
    main()
