# Petit client HTTP pour appeler notre backend FastAPI depuis les vues
# Django. Pas de lib dediee, juste httpx, l'API est petite.
import httpx
from django.conf import settings


class ErreurAPI(Exception):
    """Levee quand le backend repond une erreur (mauvais identifiants,
    token expire, film introuvable...). Le message vient directement du
    'detail' renvoye par FastAPI."""


def login(mail: str, mot_de_passe: str) -> dict:
    reponse = httpx.post(
        f"{settings.BACKEND_API_URL}/auth/login",
        json={"mail": mail, "mot_de_passe": mot_de_passe},
        timeout=10,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de connexion"))
    return reponse.json()


def films_a_venir(token: str) -> list[dict]:
    reponse = httpx.get(
        f"{settings.BACKEND_API_URL}/films-a-venir",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de recuperation des films"))
    return reponse.json()


def predict(id_oeuvre: int, token: str) -> dict:
    reponse = httpx.post(
        f"{settings.BACKEND_API_URL}/predict",
        json={"id_oeuvre": id_oeuvre},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de prediction"))
    return reponse.json()


def relancer_predictions(token: str) -> dict:
    reponse = httpx.post(
        f"{settings.BACKEND_API_URL}/predictions/relancer",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur lors de la relance"))
    return reponse.json()


def historique_predictions(token: str) -> list[dict]:
    reponse = httpx.get(
        f"{settings.BACKEND_API_URL}/predictions/historique",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de recuperation de l'historique"))
    return reponse.json()


def metriques_brutes(token: str) -> str:
    """Renvoie le texte brut expose par /metrics (format Prometheus),
    parse ensuite cote vue pour en tirer quelques chiffres simples."""
    reponse = httpx.get(f"{settings.BACKEND_API_URL}/metrics", timeout=10)
    if reponse.status_code != 200:
        raise ErreurAPI("Erreur de recuperation des metriques")
    return reponse.text
