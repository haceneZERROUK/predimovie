# Route qui liste les films de la prochaine semaine de sortie en salle -
# mercredi a venir jusqu'au samedi qui suit inclus (4 jours), pas n'importe
# quel film "dans le futur" : la plupart des sorties sont le mercredi en
# France, mais certaines (avant-premieres, sorties limitees) tombent le
# jeudi/vendredi/samedi de la meme semaine - cf audit de la base.
#
# Si cette fenetre precise est vide (le pipeline de scraping n8n n'a pas
# encore rattrape la semaine en cours - tourne le lundi), on retombe sur la
# semaine PRECEDENTE plutot que de renvoyer une page vide : ces films-la sont
# deja sortis mais leurs vraies entrees n'ont pas encore ete remontees
# (entrees_premiere_semaine toujours NULL), donc encore legitimement "a
# prevoir" en attendant le prochain passage du pipeline. Mieux vaut ca qu'un
# film isole a plusieurs semaines de la, qui n'a aucun rapport avec ce que
# l'utilisateur programme cette semaine.
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import extract, func, or_

from backend.auth import utilisateur_connecte
from backend.schemas import FilmAVenir
from database.base import SessionLocal
from database.models import Oeuvre

router = APIRouter()

# largeur de la fenetre d'une semaine de sortie : mercredi + 3 jours =
# mercredi, jeudi, vendredi, samedi inclus (dimanche exclu, deja la semaine
# suivante commerciale au cinema)
LARGEUR_FENETRE = timedelta(days=3)


def _prochain_mercredi() -> date:
    """Meme calcul que data_engineering/pipeline.py : duplique ici plutot
    que partage, pour ne pas faire dependre le backend du scraper (2
    services separes, chacun avec son propre Dockerfile)."""
    aujourdhui = date.today()
    jours_a_ajouter = (2 - aujourdhui.weekday()) % 7  # lundi=0 ... mercredi=2
    return aujourdhui + timedelta(days=jours_a_ajouter)


def _mercredi_de_la_semaine(jour: date) -> date:
    """Ramene une date quelconque au mercredi de sa semaine (utilise pour
    ancrer la fenetre de fallback sur la bonne semaine, quel que soit le
    jour exact du dernier film trouve)."""
    return jour - timedelta(days=(jour.weekday() - 2) % 7)


def _filtres_film_predictible(session):
    """Filtres communs : pas encore sorti, fiche TMDB complete, pas une
    ressortie. Reutilises pour la fenetre normale et pour le fallback."""
    return (
        Oeuvre.entrees_premiere_semaine.is_(None),
        # pas de fiche TMDB = pas de casting/genre/notes = pas assez
        # d'infos pour une prediction fiable (juste des valeurs par
        # defaut identiques pour tous ces films)
        Oeuvre.id_tmdb.isnot(None),
        # ressorties en salle (ex: un vieux film reprogramme des
        # annees plus tard) : meme seuil +-1 an que le matching
        # TMDB dans data_engineering/matching.py
        or_(
            Oeuvre.annee_sortie.is_(None),
            extract("year", Oeuvre.date_sortie) - Oeuvre.annee_sortie <= 1,
        ),
    )


@router.get("/films-a-venir", response_model=list[FilmAVenir])
def films_a_venir(_utilisateur: dict = Depends(utilisateur_connecte)):
    session = SessionLocal()
    try:
        mercredi = _prochain_mercredi()
        filtres = _filtres_film_predictible(session)

        films = (
            session.query(Oeuvre)
            .filter(Oeuvre.date_sortie.between(mercredi, mercredi + LARGEUR_FENETRE), *filtres)
            .all()
        )

        if not films:
            # rien pour la fenetre mercredi-samedi la plus proche (n8n pas
            # encore passe) : on retombe sur la semaine precedente la plus
            # recente qui a encore des films en attente de vrais resultats.
            # ancre sur le mercredi de cette semaine-la (pas juste "-3 jours"
            # depuis la derniere date trouvee) pour retomber sur la meme
            # fenetre mercredi-samedi que la recherche normale, meme si le
            # dernier film trouve n'est pas lui-meme un mercredi.
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
