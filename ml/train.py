# Entraine plusieurs modeles pour predire entrees_premiere_semaine, avec
# une recherche d'hyperparametres sur chacun, et logue tout dans mlflow
# (metriques, meilleurs parametres, features les plus importantes).
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

mlflow.set_experiment("predimovie-entrees-premiere-semaine")

CV = 5
N_ITER_RANDOM_SEARCH = 40

# un film au-dessus de ce seuil est considere "gros film" pour le calcul
# du rmse separe (diagnostic : est-ce qu'on est vraiment meilleur sur les
# blockbusters, ou juste sur la masse des petits films ?)
SEUIL_GROS_FILM = 500_000

CHEMIN_CHAMPION = "ml/modele_champion.joblib"
CHEMIN_METRIQUES_CHAMPION = "ml/modele_champion_metrics.json"

# suite a l'incident V7 (poids par categorie trop agressifs, R2 0.264->0.072
# deploye sans etre remarque avant un redemarrage manuel, cf rapport E5) :
# on ne remplace plus le champion en place que si le nouveau rmse ne se
# degrade pas de plus de 5% par rapport a lui.
SEUIL_DEGRADATION_RMSE = 0.05


def doit_remplacer_champion(
    nouveau_rmse: float, ancien_rmse: float | None, seuil: float = SEUIL_DEGRADATION_RMSE
) -> bool:
    """Decide si le nouveau modele remplace le champion en place.

    Pas d'ancien champion (premier entrainement) : on remplace toujours.
    Sinon : on ne remplace que si le rmse ne s'est pas degrade de plus de
    `seuil` (5% par defaut) par rapport a l'ancien."""
    if ancien_rmse is None:
        return True
    return (nouveau_rmse - ancien_rmse) / ancien_rmse <= seuil


# V4 : on ne garde que les 2 modeles qui sont sortis devant a chaque
# iteration precedente (xgboost et catboost) - pas la peine de refaire
# tourner ridge/lasso/random_forest/gradient_boosting/hist_gradient_boosting
# a chaque fois, ils ont toujours fini derriere
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
        # thread_count=1 pareil que les autres, pour laisser la recherche
        # d'hyperparametres gerer le parallelisme toute seule
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
    """Recupere l'importance de chaque feature, peu importe le type de
    modele (arbres = feature_importances_, lineaire = valeur absolue des
    coefficients, et pour le reste -comme HistGradientBoosting qui n'a ni
    l'un ni l'autre- on calcule une permutation_importance)."""
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
    """Fait la recherche d'hyperparametres pour un modele, logue tout dans
    mlflow, et renvoie les metriques du meilleur essai pour comparer a la fin."""
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

    # entrainement sur la cible en log (les entrees c'est tres etale,
    # log1p rend la distribution plus proche d'une gaussienne). Le poids
    # (entrees brutes) dit au modele de se concentrer plus fort sur les
    # gros films : se planter dessus coute plus cher pendant l'entrainement.
    # Teste sans en V6 (priorite aux petits/moyens films), remis tel quel
    # ensuite : les petits cinemas independants programment aussi des
    # blockbusters, il faut rester bon dessus.
    recherche.fit(X_train, np.log1p(y_train_log), sample_weight=poids_train)

    # on repasse en vraies entrees pour evaluer, plus parlant que le log
    predictions_log = recherche.predict(X_test)
    predictions = np.expm1(predictions_log).clip(min=0)

    rmse = mean_squared_error(y_test, predictions) ** 0.5
    mae = mean_absolute_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    # rmse separe gros films / petits films : est-ce que la ponderation a
    # vraiment aide sur les gros, sans trop degrader le reste ?
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
        # V5 : pourquoi ce reentrainement (visible dans l'UI mlflow, onglet
        # "Tags", pour qu'on se souvienne du "pourquoi" en regardant les
        # metriques plus tard)
        mlflow.set_tag(
            "motif_reentrainement",
            "V6 : retire note_tmdb/note_imdb (data leak temporel : notes "
            "ecrasees a la valeur ACTUELLE de TMDB/IMDb a chaque passage du "
            "pipeline, donc murie post-sortie pour les donnees backfillees) ; "
            "POIDS_LISSAGE 8->2 (encodage cible acteur/realisateur/production/"
            "genre moins tire vers la moyenne globale) ; sample_weight = "
            "entrees brutes, sans ponderation par categorie (essaye en V7, "
            "gain mitige et un premier essai avec des multiplicateurs trop "
            "agressifs avait fait s'effondrer le modele - abandonne, retour "
            "a la version simple). Iteration precedente : ajoute nb_salles_predites, "
            "sortie d'un sous-modele leger (ml/salles.py) qui predit le "
            "nombre de salles en semaine 1 a partir du budget/genre/casting/"
            "saisonnalite - le vrai nb_salles_semaine1 n'existe que "
            "retrospectivement sur JPBOX, jamais disponible avant une sortie "
            "reelle (verifie en conditions reelles). Cette iteration : ajoute "
            "budget en feature directe (en plus de son usage dans le sous-modele "
            "salles). Analyse ANOVA/Pearson sur les donnees brutes (avant tout "
            "feature engineering) : budget a r=0.484 avec la cible, 2e correlation "
            "la plus forte apres les fuites connues (note_tmdb/imdb, "
            "nb_salles_semaine1) - signal fort jusque-la seulement filtre "
            "indirectement via nb_salles_predites, jamais expose tel quel au "
            "modele principal (gain reel quasi nul au final, deja capte par "
            "nb_salles_predites). Ajoute aussi acteur_habitue et "
            "realisateur_habitue (le film a-t-il un acteur/realisateur credite "
            "dans >= 10 films du train ? cf SEUIL_HABITUE) - tres significatif "
            "en ANOVA sur donnees brutes (acteur F=269.5 p=8.2e-60, "
            "realisateur F=144.3 p=5.0e-33) mais potentiellement redondant "
            "avec acteur_pop_max/realisateur_pop_max deja dans le modele "
            "(meme signal, version binaire vs continue).",
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

        # simple joblib + artifact plutot que mlflow.sklearn.log_model :
        # ce dernier bloque xgboost par securite (types "non fiables"), autant
        # avoir la meme methode de sauvegarde pour tous les modeles
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
    print("chargement des donnees depuis postgres...")
    X_train, X_test, y_train, y_test, artefacts = charger_dataset_train_test()
    print(f"{len(X_train) + len(X_test)} films, {X_train.shape[1]} features")

    # poids = entrees brutes du train : un blockbuster pese beaucoup plus
    # lourd dans la fonction de cout qu'un petit film (V3). Le poids par
    # categorie francais/gros-succes teste en V7 a ete abandonne : gain
    # mitige, et le modele s'etait effondre au premier essai avec des
    # multiplicateurs trop agressifs (cf mlflow, tag motif_reentrainement
    # des runs V7) - on revient a la version simple, plus honnete.
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
    # les artefacts (vectoriseur tf-idf, stats d'encodage, medianes...) sont
    # ce dont l'API a besoin pour construire les features d'un film tout
    # neuf de la meme facon qu'ici, sans quoi le modele recevrait des
    # colonnes incoherentes avec ce sur quoi il a ete entraine
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
