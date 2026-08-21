# Tests de _importance_features : elle doit marcher peu importe le type
# de modele (arbres, lineaire, ou ni l'un ni l'autre).
import numpy as np

from ml.train import _importance_features


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
