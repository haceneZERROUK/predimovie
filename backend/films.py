# Liste les films de la prochaine semaine de sortie : du mercredi au
# samedi. La plupart des films sortent le mercredi mais quelques uns
# (avant-premieres, sorties limitees) tombent le reste de la semaine.
# Si la fenetre est vide parce que le scraping n'est pas encore passe, on
# retombe sur la semaine d'avant au lieu de renvoyer une page vide.
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func

from backend.auth import utilisateur_connecte
from backend.filtres_oeuvres import filtres_fiche_complete, filtres_ressortie
from backend.schemas import FilmAVenir
from database.base import SessionLocal
from database.models import Oeuvre

router = APIRouter()

# mercredi + 3 jours, donc jusqu'au samedi inclus
LARGEUR_FENETRE = timedelta(days=3)


def _prochain_mercredi() -> date:
    """Date du prochain mercredi. Recopie du scraper, pour ne pas rendre
    le backend dependant de data_engineering."""
    aujourdhui = date.today()
    jours_a_ajouter = (2 - aujourdhui.weekday()) % 7  # lundi=0 ... mercredi=2
    return aujourdhui + timedelta(days=jours_a_ajouter)


def _mercredi_de_la_semaine(jour: date) -> date:
    """Ramene une date au mercredi de sa semaine."""
    return jour - timedelta(days=(jour.weekday() - 2) % 7)


def _filtres_film_predictible():
    """Filtres communs aux deux requetes : entrees pas encore connues,
    fiche TMDB presente, et pas une ressortie."""
    return (
        Oeuvre.entrees_premiere_semaine.is_(None),
        *filtres_fiche_complete(),
        *filtres_ressortie(),
    )


@router.get("/films-a-venir", response_model=list[FilmAVenir])
def films_a_venir(_utilisateur: dict = Depends(utilisateur_connecte)):
    session = SessionLocal()
    try:
        mercredi = _prochain_mercredi()
        filtres = _filtres_film_predictible()

        films = (
            session.query(Oeuvre)
            .filter(Oeuvre.date_sortie.between(mercredi, mercredi + LARGEUR_FENETRE), *filtres)
            .all()
        )

        if not films:
            # rien sur la fenetre en cours : on prend la derniere semaine
            # qui a encore des films sans resultats. On repart du mercredi
            # de cette semaine-la pour avoir la meme fenetre qu'au-dessus.
            derniere_date = (
                session.query(func.max(Oeuvre.date_sortie))
                .filter(Oeuvre.date_sortie < mercredi, *filtres)
                .scalar()
            )
            if derniere_date is not None:
                mercredi_precedent = _mercredi_de_la_semaine(derniere_date)
                films = (
                    session.query(Oeuvre)
                    .filter(
                        Oeuvre.date_sortie.between(
                            mercredi_precedent, mercredi_precedent + LARGEUR_FENETRE
                        ),
                        *filtres,
                    )
                    .all()
                )

        return [
            FilmAVenir(
                id_oeuvre=f.id_oeuvre,
                nom_francais=f.nom_francais,
                date_sortie=f.date_sortie,
                synopsis=f.synopsis,
            )
            for f in films
        ]
    finally:
        session.close()
