# App FastAPI : connexion (JWT) + prediction. Le frontend Django appelle
# ces routes en HTTP.
from fastapi import FastAPI

from backend.auth import router as auth_router
from backend.predict import router as predict_router

app = FastAPI(title="Predimovie - Backend")

app.include_router(auth_router)
app.include_router(predict_router)


@app.get("/health")
def health():
    """Utilise par docker-compose pour verifier que le service tourne bien."""
    return {"status": "ok"}
