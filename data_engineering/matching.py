# Ce module sert à vérifier si un film trouvé sur JPBOX et un film trouvé
# sur TMDB sont bien LE MEME film, alors que les titres ne sont parfois
# pas écrits pareil d'une source à l'autre (accents, articles, ponctuation).
import re
import unicodedata

from rapidfuzz import fuzz

# Petits mots en début de titre qu'on ignore pour mieux comparer.
# "l " correspond à "l'" une fois l'apostrophe transformée en espace.
ARTICLES = ("le ", "la ", "les ", "l ", "the ", "a ", "an ")


def nettoyer_annotations(titre: str) -> str:
    """Enlève une annotation JPBOX en fin de titre, ex: "(Rep. 2026)" pour
    une reprise en salle. jpbox.py a déjà retiré les parenthèses qui
    contiennent juste une année ; celles qui restent ne font que polluer
    la recherche et la comparaison TMDB."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", titre).strip()


def normaliser_titre(titre: str) -> str:
    """Nettoie un titre pour pouvoir le comparer facilement :
    minuscules, sans accents, sans ponctuation, sans article en tête."""
    titre = titre.lower().strip()

    # enlève les accents (é -> e, à -> a, ...)
    titre = unicodedata.normalize("NFKD", titre)
    titre = "".join(caractere for caractere in titre if not unicodedata.combining(caractere))

    # ne garde que les lettres, les chiffres et les espaces
    titre = "".join(c if c.isalnum() or c.isspace() else " " for c in titre)
    titre = " ".join(titre.split())

    for article in ARTICLES:
        if titre.startswith(article):
            titre = titre[len(article) :]
            break

    return titre.strip()


def se_ressemblent(titre_a: str, titre_b: str, seuil: int = 85) -> bool:
    """Dit si 2 titres sont probablement le même film.
    Le score de ressemblance va de 0 (rien à voir) à 100 (identiques)."""
    score = fuzz.ratio(normaliser_titre(titre_a), normaliser_titre(titre_b))
    return score >= seuil


def meme_film(titre_jpbox: str, annee_jpbox: int | None, resultat_tmdb: dict) -> bool:
    """Valide qu'un résultat TMDB correspond bien au film JPBOX :
    les titres doivent se ressembler ET l'année de sortie doit coller
    (±1 an, pour absorber le décalage entre sortie française et étrangère)."""
    titre_jpbox = nettoyer_annotations(titre_jpbox)
    titre_tmdb = resultat_tmdb.get("title", "")
    if not se_ressemblent(titre_jpbox, titre_tmdb):
        return False

    if annee_jpbox is None:
        return True  # pas d'année côté JPBOX : on se contente du titre

    date_sortie = resultat_tmdb.get("release_date") or ""
    if len(date_sortie) < 4:
        return False

    annee_tmdb = int(date_sortie[:4])
    return abs(annee_tmdb - annee_jpbox) <= 1
