# Tache mensuelle, lancee par un cron Railway : demande au backend de
# reentrainer le modele.
import os

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend.railway.internal:8000")
TRAIN_API_KEY = os.environ.get("TRAIN_API_KEY", "")


def main():
    # timeout court : la route repond tout de suite, l'entrainement tourne
    # en arriere-plan (25-40 min)
    reponse = httpx.post(
        f"{BACKEND_URL}/admin/reentrainer-modele",
        headers={"X-Api-Key": TRAIN_API_KEY},
        timeout=5,
    )
    reponse.raise_for_status()
    print(f"reentrainement declenche : {reponse.json()}")


if __name__ == "__main__":
    main()
