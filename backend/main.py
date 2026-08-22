# App FastAPI : connexion (JWT) + prediction. Le frontend Django appelle
# ces routes en HTTP.
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from backend.auth import router as auth_router
from backend.films import router as films_router
from backend.predict import router as predict_router
from backend.predictions_admin import router as predictions_admin_router

app = FastAPI(title="Predimovie - Backend")

app.include_router(auth_router)
app.include_router(predict_router)
app.include_router(films_router)
app.include_router(predictions_admin_router)

# expose /metrics (format Prometheus) : nb de requetes, temps de reponse,
# codes d'erreur, par route. Voir rapport_api.pdf pour les indicateurs
# a suivre a partir de ca.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    """Utilise par docker-compose pour verifier que le service tourne bien."""
    return {"status": "ok"}
