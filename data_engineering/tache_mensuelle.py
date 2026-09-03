# Declenche le reentrainement mensuel du modele (route deja protegee par
# TRAIN_API_KEY, cf backend/reentrainement.py). Pense a etre lance en cron
# Railway - remplace le workflow n8n "reentrainement_mensuel".
import os

import httpx

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend.railway.internal:8000")
TRAIN_API_KEY = os.environ.get("TRAIN_API_KEY", "")


def main():
    # meme timeout court que dans le workflow n8n : la route repond tout de
    # suite (entrainement lance en arriere-plan, ca prend 25-40 min)
    reponse = httpx.post(
        f"{BACKEND_URL}/admin/reentrainer-modele",
        headers={"X-Api-Key": TRAIN_API_KEY},
        timeout=5,
    )
    reponse.raise_for_status()
    print(f"reentrainement declenche : {reponse.json()}")


if __name__ == "__main__":
    main()
