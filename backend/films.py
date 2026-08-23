# Route qui liste les films qui sortent le mercredi a venir (pas
# n'importe quel film "dans le futur"), pour que le frontend propose une
# prediction sur les vraies sorties de la semaine, sans avoir a
# interroger Postgres lui-meme.
from datetime import date, timedelta

from fastapi import APIRouter, Depends

from backend.auth import utilisateur_connecte
from backend.schemas import FilmAVenir
from database.base import SessionLocal
from database.models import Oeuvre

router = APIRouter()


def _prochain_mercredi() -> date:
    """Meme calcul que data_engineering/pipeline.py : duplique ici plutot
    que partage, pour ne pas faire dependre le backend du scraper (2
    services separes, chacun avec son propre Dockerfile)."""
    aujourdhui = date.today()
    jours_a_ajouter = (2 - aujourdhui.weekday()) % 7  # lundi=0 ... mercredi=2
    return aujourdhui + timedelta(days=jours_a_ajouter)


@router.get("/films-a-venir", response_model=list[FilmAVenir])
def films_a_venir(_utilisateur: dict = Depends(utilisateur_connecte)):
    session = SessionLocal()
    try:
        films = (
            session.query(Oeuvre)
            .filter(
                Oeuvre.entrees_premiere_semaine.is_(None),
                Oeuvre.date_sortie == _prochain_mercredi(),
            )
            .all()
        )
        return [
            FilmAVenir(
                id_oeuvre=f.id_oeuvre, nom_francais=f.nom_francais, date_sortie=f.date_sortie
            )
            for f in films
        ]
    finally:
        session.close()
