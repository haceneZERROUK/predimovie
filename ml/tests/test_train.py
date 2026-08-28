# Tests de _importance_features (marche peu importe le type de modele) et
# de doit_remplacer_champion (garde-fou anti-regression, cf incident V7
# documente dans rapport_E5 : un entrainement degrade ne doit plus ecraser
# le champion en place sans avertir).
import numpy as np

from ml.train import SEUIL_DEGRADATION_RMSE, _importance_features, doit_remplacer_champion


class _ModeleAvecFeatureImportances:
    feature_importances_ = np.array([0.1, 0.7, 0.2])


class _ModeleLineaire:
    coef_ = np.array([-5.0, 1.0, 0.5])


def test_importance_features_avec_arbre_trie_par_importance_decroissante():
    modele = _ModeleAvecFeatureImportances()
    resultat = _importance_features(modele, ["a", "b", "c"], X_test=None, y_test_log=None)

    assert list(resultat["feature"]) == ["b", "c", "a"]
    assert resultat["importance"].iloc[0] == 0.7


def test_importance_features_avec_modele_lineaire_prend_la_valeur_absolue():
    # le coefficient le plus important est -5.0 (le plus gros en valeur
    # absolue), meme s'il est negatif
    modele = _ModeleLineaire()
    resultat = _importance_features(modele, ["a", "b", "c"], X_test=None, y_test_log=None)

    assert resultat["feature"].iloc[0] == "a"
    assert resultat["importance"].iloc[0] == 5.0


def test_doit_remplacer_champion_sans_ancien_modele():
    # premier entrainement (pas de champion existant) : on sauvegarde toujours
    assert doit_remplacer_champion(nouveau_rmse=300_000, ancien_rmse=None) is True


def test_doit_remplacer_champion_meilleur_ou_egal():
    assert doit_remplacer_champion(nouveau_rmse=250_000, ancien_rmse=260_000) is True
    assert doit_remplacer_champion(nouveau_rmse=260_000, ancien_rmse=260_000) is True


def test_doit_remplacer_champion_legere_degradation_toleree():
    # 3% de degradation, sous le seuil (5% par defaut) : on remplace quand meme
    assert doit_remplacer_champion(nouveau_rmse=260_000 * 1.03, ancien_rmse=260_000) is True


def test_doit_remplacer_champion_refuse_si_degradation_trop_forte():
    # cas de l'incident V7 : R2 0.264 -> 0.072, rmse degrade de +19%, bien
    # au-dela du seuil tolere -> on ne remplace pas le champion en place
    assert doit_remplacer_champion(nouveau_rmse=303_056, ancien_rmse=254_654) is False


def test_seuil_par_defaut_est_cinq_pourcent():
    assert SEUIL_DEGRADATION_RMSE == 0.05
