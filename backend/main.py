# L'app FastAPI, ou on branche tous les routers. C'est ce que le frontend
# Django appelle en HTTP.
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
    """Ajoute des en-tetes de securite sur chaque reponse : pas de sniffing
    MIME, pas d'iframe, pas de referer envoye a l'exterieur."""

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

# expose /metrics au format Prometheus : nb de requetes, temps de reponse
# et codes d'erreur par route
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health():
    """Route de healthcheck."""
    return {"status": "ok"}
