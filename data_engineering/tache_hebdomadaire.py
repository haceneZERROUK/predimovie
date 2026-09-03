# Tache hebdo, lancee par un cron Railway : scrape les sorties de la
# semaine, extrait les mots-cles, met a jour les predictions de salles et
# demande au backend de relancer les predictions d'entrees.
import os

import httpx

from data_engineering.mots_cles import enrichir_les_films_sans_mots_cles
from data_engineering.pipeline import prochain_mercredi, traiter_films_a_venir
from database.base import SessionLocal
from ml.salles import entrainer_et_predire_pour_tous, sauvegarder_predictions_en_base

BACKEND_URL = os.environ.get("BACKEND_URL", "http://backend.railway.internal:8000")
PREDICTION_API_KEY = os.environ.get("PREDICTION_API_KEY", "")


def relancer_predictions_backend() -> None:
    reponse = httpx.post(
        f"{BACKEND_URL}/admin/predictions/relancer",
        headers={"X-Api-Key": PREDICTION_API_KEY},
        timeout=60,
    )
    reponse.raise_for_status()
    print(f"predictions relancees : {reponse.json()}")


def main():
    session = SessionLocal()
    try:
        date_sortie = prochain_mercredi()
        nb_films = traiter_films_a_venir(session, date_sortie=date_sortie)
        print(f"{nb_films} films scrapes pour la sortie du {date_sortie}")

        nb_mots_cles = enrichir_les_films_sans_mots_cles(session)
        print(f"{nb_mots_cles} films enrichis avec des mots-cles")
    finally:
        session.close()

    predictions_salles, _ = entrainer_et_predire_pour_tous()
    sauvegarder_predictions_en_base(predictions_salles)

    relancer_predictions_backend()


if __name__ == "__main__":
    main()
