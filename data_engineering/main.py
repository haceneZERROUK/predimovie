# API du scraper : N8n appelle ces routes en HTTP pour déclencher
# les différentes étapes du pipeline (voir data_engineering/pipeline.py).
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException

from data_engineering.config import JPBOX_VUE_FRANCE, SCRAPER_API_KEY
from data_engineering.pipeline import backfill as lancer_backfill
from data_engineering.pipeline import traiter_entrees_semaine, traiter_films_a_venir
from database.base import SessionLocal

app = FastAPI(title="Predimovie - Scraper")


def verifier_cle_api(x_api_key: str = Header(default="")):
    """Vérifie que l'appelant (N8n) connaît le secret partagé.
    Pas de JWT ici : il n'y a pas d'utilisateur, juste une machine qui
    déclenche le scraping."""
    if x_api_key != SCRAPER_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@app.post("/scrape/upcoming", dependencies=[Depends(verifier_cle_api)])
def scrape_upcoming(date_sortie: date | None = None):
    """Flux A : récupère tous les films qui sortent un mercredi donné
    (le prochain par défaut) via le calendrier JPBOX."""
    session = SessionLocal()
    try:
        nb_films = traiter_films_a_venir(session, date_sortie=date_sortie)
        return {"nb_films_traites": nb_films}
    finally:
        session.close()


@app.post("/scrape/entrees", dependencies=[Depends(verifier_cle_api)])
def scrape_entrees(idsem: int, vue: int = JPBOX_VUE_FRANCE):
    """Flux B : récupère les entrées de première semaine pour idsem."""
    session = SessionLocal()
    try:
        nb_maj = traiter_entrees_semaine(session, idsem, vue)
        return {"nb_films_mis_a_jour": nb_maj}
    finally:
        session.close()


@app.post("/scrape/backfill", dependencies=[Depends(verifier_cle_api)])
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
    """Utilisé par docker-compose pour vérifier que le service tourne bien.
    Pas protégé : ne renvoie aucune donnée sensible."""
    return {"status": "ok"}
