# Verifie le rechargement a chaud du modele (backend/moteur_prediction.py) :
# necessaire depuis que le reentrainement mensuel peut remplacer
# modele_champion.joblib sans redemarrer l'API. On utilise de faux fichiers
# joblib (pas de vrai modele ML) pour tester juste la logique de cache.
import os
import time

import joblib

import backend.moteur_prediction as mp


def test_charge_le_modele_au_premier_appel(monkeypatch, tmp_path):
    chemin_modele = tmp_path / "modele.joblib"
    chemin_artefacts = tmp_path / "artefacts.joblib"
    joblib.dump("modele-v1", chemin_modele)
    joblib.dump("artefacts-v1", chemin_artefacts)

    monkeypatch.setattr(mp, "CHEMIN_MODELE", str(chemin_modele))
    monkeypatch.setattr(mp, "CHEMIN_ARTEFACTS", str(chemin_artefacts))
    monkeypatch.setattr(mp, "_modele", None)
    monkeypatch.setattr(mp, "_artefacts", None)
    monkeypatch.setattr(mp, "_derniere_maj_modele", None)

    mp._charger_modele_si_necessaire()

    assert mp._modele == "modele-v1"
    assert mp._artefacts == "artefacts-v1"


def test_recharge_seulement_si_le_fichier_a_change(monkeypatch, tmp_path):
    chemin_modele = tmp_path / "modele.joblib"
    chemin_artefacts = tmp_path / "artefacts.joblib"
    joblib.dump("modele-v1", chemin_modele)
    joblib.dump("artefacts-v1", chemin_artefacts)

    monkeypatch.setattr(mp, "CHEMIN_MODELE", str(chemin_modele))
    monkeypatch.setattr(mp, "CHEMIN_ARTEFACTS", str(chemin_artefacts))
    monkeypatch.setattr(mp, "_modele", None)
    monkeypatch.setattr(mp, "_artefacts", None)
    monkeypatch.setattr(mp, "_derniere_maj_modele", None)

    mp._charger_modele_si_necessaire()
    assert mp._modele == "modele-v1"

    # rappel sans que le fichier ait change : reste sur la meme version
    mp._charger_modele_si_necessaire()
    assert mp._modele == "modele-v1"

    # le reentrainement mensuel remplace le fichier par une nouvelle version
    # (mtime deliberement decale pour ne pas dependre de la resolution du fs)
    joblib.dump("modele-v2", chemin_modele)
    joblib.dump("artefacts-v2", chemin_artefacts)
    plus_tard = time.time() + 10
    os.utime(chemin_modele, (plus_tard, plus_tard))

    mp._charger_modele_si_necessaire()

    assert mp._modele == "modele-v2"
    assert mp._artefacts == "artefacts-v2"
