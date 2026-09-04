# Filtres partages entre le classement des sorties a venir et l'historique
# predit/reel.
#
# Avant, seul le classement filtrait : un film ecarte la-bas reapparaissait
# dans l'historique, ce qui donnait des lignes en double a l'ecran.
from sqlalchemy import extract, or_

from database.models import Oeuvre


def filtres_ressortie():
    """Ecarte les reprises en salle : un film ressorti des annees apres sa
    production n'est pas une nouvelle sortie et ne se compare pas aux
    autres. Meme ecart d'1 an que le matching TMDB."""
    return (
        or_(
            Oeuvre.annee_sortie.is_(None),
            extract("year", Oeuvre.date_sortie) - Oeuvre.annee_sortie <= 1,
        ),
    )


def filtres_fiche_complete():
    """Sans fiche TMDB on n'a ni casting ni genre, la prediction ne vaudrait
    rien."""
    return (Oeuvre.id_tmdb.isnot(None),)
