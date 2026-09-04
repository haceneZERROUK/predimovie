# Filtres partages entre le classement des sorties a venir et l'historique
# predit/reel.
#
# Avant, seul le classement filtrait : un film ecarte la-bas reapparaissait
# dans l'historique, ce qui donnait des lignes en double a l'ecran.
import re
import unicodedata

from sqlalchemy import extract, or_

from database.models import Oeuvre

# articles retires en debut de titre avant comparaison, comme dans
# data_engineering.matching
ARTICLES = ("le ", "la ", "les ", "l ", "the ", "a ", "an ")


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


def _sans_annotations(titre: str) -> str:
    """Vire ce qu'il y a entre parentheses a la fin, genre "(Rep. 2026)"."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", titre or "").strip()


def cle_de_regroupement(oeuvre) -> tuple:
    """Ce qui identifie un film pour dire que deux lignes sont la meme
    sortie : son titre normalise et sa date.

    On n'utilise pas id_tmdb, alors que ce serait plus direct : le
    rapprochement TMDB est flou et donne le meme id a des films
    differents. "Toy Story 5" pointe sur la fiche de "Toy Story",
    "Zootopie 2" sur celle de "Zootopie". Regrouper la-dessus ferait
    disparaitre une suite de l'ecran.

    Meme normalisation que data_engineering.matching, recopiee ici parce
    que ce paquet n'est pas dans l'image du backend."""
    titre = _sans_annotations(oeuvre.nom_francais).lower()
    titre = unicodedata.normalize("NFKD", titre)
    titre = "".join(c for c in titre if not unicodedata.combining(c))
    titre = "".join(c if c.isalnum() or c.isspace() else " " for c in titre)
    titre = " ".join(titre.split())
    for article in ARTICLES:
        if titre.startswith(article):
            titre = titre[len(article) :]
            break
    return (titre, oeuvre.date_sortie)
