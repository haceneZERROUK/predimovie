# On ne lance jamais le vrai entrainement ici, on le remplace par un faux
# pour tester juste la route (cle API et tache de fond).
from fastapi.testclient import TestClient

import backend.reentrainement as reentrainement_module
from backend.main import app

client = TestClient(app)


def test_refuse_sans_bonne_cle_api(monkeypatch):
    monkeypatch.setattr(reentrainement_module, "TRAIN_API_KEY", "bon-secret")
    reponse = client.post("/admin/reentrainer-modele", headers={"x-api-key": "mauvais-secret"})
    assert reponse.status_code == 401


def test_lance_le_reentrainement_en_tache_de_fond(monkeypatch):
    appels = []
    monkeypatch.setattr(reentrainement_module, "TRAIN_API_KEY", "bon-secret")
    monkeypatch.setattr(reentrainement_module, "reentrainer_le_modele", lambda: appels.append(1))

    reponse = client.post("/admin/reentrainer-modele", headers={"x-api-key": "bon-secret"})

    assert reponse.status_code == 200
    assert reponse.json() == {"statut": "reentrainement lance en arriere-plan"}
    assert appels == [1]


def test_echec_du_reentrainement_ne_fait_pas_planter_la_route(monkeypatch, caplog):
    def _echoue():
        raise RuntimeError("panne simulee")

    monkeypatch.setattr(reentrainement_module, "TRAIN_API_KEY", "bon-secret")
    monkeypatch.setattr(reentrainement_module, "reentrainer_le_modele", _echoue)

    reponse = client.post("/admin/reentrainer-modele", headers={"x-api-key": "bon-secret"})

    assert reponse.status_code == 200
    assert "Echec du reentrainement" in caplog.text
