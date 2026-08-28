# App FastAPI : connexion (JWT) + prediction. Le frontend Django appelle
# ces routes en HTTP.
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from backend.auth import router as auth_router
from backend.comptes import router as comptes_router
from backend.films import router as films_router
from backend.predict import router as predict_router
from backend.predictions_admin import router as predictions_admin_router
from backend.reentrainement import router as reentrainement_router


class EntetesSecuriteMiddleware(BaseHTTPMiddleware):
    """Ajoute quelques en-tetes de securite basiques (OWASP - mauvaise
    configuration) a chaque reponse : pas de sniffing MIME, pas d'affichage
    dans une iframe, pas de fuite d'URL vers un site externe."""

    async def dispatch(self, request, call_next):
        reponse = await call_next(request)
        reponse.headers["X-Content-Type-Options"] = "nosniff"
        reponse.headers["X-Frame-Options"] = "DENY"
        reponse.headers["Referrer-Policy"] = "no-referrer"
        return reponse


app = FastAPI(title="Predimovie - Backend")
app.add_middleware(EntetesSecuriteMiddleware)

app.include_router(auth_router)
app.include_router(predict_router)
app.include_router(films_router)
app.include_router(predictions_admin_router)
app.include_router(comptes_router)
app.include_router(reentrainement_router)

# expose /metrics (format Prometheus) : nb de requetes, temps de reponse,
# codes d'erreur, par route. Voir rapport_api.pdf pour les indicateurs
# a suivre a partir de ca.
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    """Utilise par docker-compose pour verifier que le service tourne bien."""
    return {"status": "ok"}
