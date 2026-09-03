# Verifie que le middleware d'en-tetes de securite s'applique sur toutes
# les routes et pas juste une
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_reponse_contient_les_entetes_de_securite():
    reponse = client.get("/health")

    assert reponse.headers["x-content-type-options"] == "nosniff"
    assert reponse.headers["x-frame-options"] == "DENY"
    assert reponse.headers["referrer-policy"] == "no-referrer"
