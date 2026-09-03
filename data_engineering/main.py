# Petite API pour declencher les etapes du pipeline en HTTP
from datetime import date

from fastapi import Depends, FastAPI, Header, HTTPException

from data_engineering.config import JPBOX_VUE_FRANCE, SCRAPER_API_KEY
from data_engineering.pipeline import backfill as lancer_backfill
from data_engineering.pipeline import traiter_entrees_semaine, traiter_films_a_venir
from database.base import SessionLocal

app = FastAPI(title="Predimovie - Scraper")


def verifier_cle_api(x_api_key: str = Header(default="")):
    """Verifie la cle API passee dans l'en-tete X-Api-Key."""
    if x_api_key != SCRAPER_API_KEY:
        raise HTTPException(status_code=401, detail="Clé API invalide")


@app.post("/scrape/upcoming", dependencies=[Depends(verifier_cle_api)])
def scrape_upcoming(date_sortie: date | None = None):
    """Flux A : les films qui sortent un mercredi donne, le prochain par defaut."""
    session = SessionLocal()
    try:
        nb_films = traiter_films_a_venir(session, date_sortie=date_sortie)
        return {"nb_films_traites": nb_films}
    finally:
        session.close()


@app.post("/scrape/entrees", dependencies=[Depends(verifier_cle_api)])
def scrape_entrees(idsem: int, vue: int = JPBOX_VUE_FRANCE):
    """Flux B : les entrees de 1ere semaine pour la semaine idsem."""
    session = SessionLocal()
    try:
        nb_maj = traiter_entrees_semaine(session, idsem, vue)
        return {"nb_films_mis_a_jour": nb_maj}
    finally:
        session.close()


@app.post("/scrape/backfill", dependencies=[Depends(verifier_cle_api)])
def scrape_backfill(idsem_debut: int, idsem_fin: int, vue: int = JPBOX_VUE_FRANCE):
    """Rejoue le flux B sur une plage de semaines."""
    session = SessionLocal()
    try:
        total = lancer_backfill(session, idsem_debut, idsem_fin, vue)
        return {"nb_films_mis_a_jour": total}
    finally:
        session.close()


@app.get("/health")
def health():
    """Route de healthcheck, pas protegee."""
    return {"status": "ok"}
