# Appels au backend FastAPI depuis les vues Django, en httpx
import httpx
from django.conf import settings


class ErreurAPI(Exception):
    """Levee quand le backend repond une erreur. Le message reprend le
    champ 'detail' de la reponse."""


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


def historique_predictions(token: str, semaine: str | None = None) -> dict:
    reponse = httpx.get(
        f"{settings.BACKEND_API_URL}/predictions/historique",
        params={"semaine": semaine} if semaine else None,
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de recuperation de l'historique"))
    return reponse.json()


def lister_comptes(token: str) -> list[dict]:
    reponse = httpx.get(
        f"{settings.BACKEND_API_URL}/comptes",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 200:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de recuperation des comptes"))
    return reponse.json()


def creer_compte(mail: str, mot_de_passe: str, nom_cinema: str, token: str) -> dict:
    reponse = httpx.post(
        f"{settings.BACKEND_API_URL}/comptes",
        json={"mail": mail, "mot_de_passe": mot_de_passe, "nom_cinema": nom_cinema},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 201:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de creation du compte"))
    return reponse.json()


def supprimer_compte(id_compte: int, token: str) -> None:
    reponse = httpx.delete(
        f"{settings.BACKEND_API_URL}/comptes/{id_compte}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if reponse.status_code != 204:
        raise ErreurAPI(reponse.json().get("detail", "Erreur de suppression du compte"))


def metriques_brutes(token: str) -> str:
    """Renvoie le texte brut de /metrics, parse ensuite par
    metrics_parser."""
    reponse = httpx.get(f"{settings.BACKEND_API_URL}/metrics", timeout=10)
    if reponse.status_code != 200:
        raise ErreurAPI("Erreur de recuperation des metriques")
    return reponse.text
