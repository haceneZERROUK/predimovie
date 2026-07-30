# API du scraper : N8n appelle ces routes en HTTP pour déclencher
# les différentes étapes du pipeline (voir data_engineering/pipeline.py).
from fastapi import FastAPI

from data_engineering.config import JPBOX_VUE_FRANCE
from data_engineering.pipeline import backfill as lancer_backfill
from data_engineering.pipeline import traiter_entrees_semaine, traiter_films_a_venir
from database.base import SessionLocal

app = FastAPI(title="Predimovie - Scraper")


@app.post("/scrape/upcoming")
def scrape_upcoming():
    """Flux A : récupère les films bientôt en salle (métadonnées TMDB)."""
    session = SessionLocal()
    try:
        nb_films = traiter_films_a_venir(session)
        return {"nb_films_traites": nb_films}
    finally:
        session.close()


@app.post("/scrape/entrees")
def scrape_entrees(idsem: int, vue: int = JPBOX_VUE_FRANCE):
    """Flux B : récupère les entrées de première semaine pour idsem."""
    session = SessionLocal()
    try:
        nb_maj = traiter_entrees_semaine(session, idsem, vue)
        return {"nb_films_mis_a_jour": nb_maj}
    finally:
        session.close()


@app.post("/scrape/backfill")
def scrape_backfill(idsem_debut: int, idsem_fin: int, vue: int = JPBOX_VUE_FRANCE):
    """Rattrapage historique sur une plage de semaines JPBOX."""
    session = SessionLocal()
    try:
        total = lancer_backfill(session, idsem_debut, idsem_fin, vue)
        return {"nb_films_mis_a_jour": total}
    finally:
        session.close()


@app.get("/health")
def health():
    """Utilisé par docker-compose pour vérifier que le service tourne bien."""
    return {"status": "ok"}
