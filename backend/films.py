# Route qui liste les films pas encore sortis (pas d'entrees connues en
# base), pour que le frontend sache sur quels films proposer une
# prediction sans avoir a interroger Postgres lui-meme.
from fastapi import APIRouter, Depends

from backend.auth import utilisateur_connecte
from backend.schemas import FilmAVenir
from database.base import SessionLocal
from database.models import Oeuvre

router = APIRouter()


@router.get("/films-a-venir", response_model=list[FilmAVenir])
def films_a_venir(_utilisateur: dict = Depends(utilisateur_connecte)):
    session = SessionLocal()
    try:
        films = session.query(Oeuvre).filter(Oeuvre.entrees_premiere_semaine.is_(None)).all()
        return [
            FilmAVenir(
                id_oeuvre=f.id_oeuvre, nom_francais=f.nom_francais, date_sortie=f.date_sortie
            )
            for f in films
        ]
    finally:
        session.close()
