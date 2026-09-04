# Compare les titres de films entre JPBOX/AlloCine et TMDB, vu qu'ils ne
# sont pas ecrits pareil d'une source a l'autre
import re
import unicodedata

from rapidfuzz import fuzz

# articles qu'on retire en debut de titre avant de comparer
# ("l " c'est "l'" une fois l'apostrophe remplacee par un espace)
ARTICLES = ("le ", "la ", "les ", "l ", "the ", "a ", "an ")


def nettoyer_annotations(titre: str) -> str:
    """Vire ce qu'il y a entre parentheses a la fin du titre, genre
    "(Rep. 2026)" pour une reprise en salle."""
    return re.sub(r"\s*\([^)]*\)\s*$", "", titre).strip()


def normaliser_titre(titre: str) -> str:
    """Met le titre en minuscules, sans accents, sans ponctuation et sans
    article devant, pour pouvoir le comparer."""
    titre = titre.lower().strip()

    # accents : e -> e, a -> a...
    titre = unicodedata.normalize("NFKD", titre)
    titre = "".join(caractere for caractere in titre if not unicodedata.combining(caractere))

    # on garde que les lettres, chiffres et espaces
    titre = "".join(c if c.isalnum() or c.isspace() else " " for c in titre)
    titre = " ".join(titre.split())

    for article in ARTICLES:
        if titre.startswith(article):
            titre = titre[len(article) :]
            break

    return titre.strip()


# suites ecrites en chiffres romains, pour les comparer aux arabes :
# "Bad Boys II" et "Bad Boys 2", c'est le meme film
ROMAINS = {"ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9, "x": 10}


def numero_de_suite(titre: str) -> int | None:
    """Le numero de suite a la fin du titre, s'il y en a un.

    "Toy Story 5" et "Toy Story" ressemblent a 90 %, assez pour que le
    rapprochement les confonde alors que ce sont deux films. Comparer ce
    numero les separe."""
    mots = normaliser_titre(nettoyer_annotations(titre)).split()
    if len(mots) < 2:
        # un titre qui n'est qu'un nombre ("1917") n'est pas une suite
        return None
    dernier = mots[-1]
    if dernier.isdigit():
        return int(dernier)
    return ROMAINS.get(dernier)


def se_ressemblent(titre_a: str, titre_b: str, seuil: int = 85) -> bool:
    """True si les 2 titres se ressemblent assez (score de 0 a 100)."""
    score = fuzz.ratio(normaliser_titre(titre_a), normaliser_titre(titre_b))
    return score >= seuil


def meme_film(titre_jpbox: str, annee_jpbox: int | None, resultat_tmdb: dict) -> bool:
    """Verifie qu'un resultat TMDB est bien le film JPBOX : les titres se
    ressemblent et l'annee colle a 1 an pres (decalage sortie FR/etranger)."""
    titre_jpbox = nettoyer_annotations(titre_jpbox)
    titre_tmdb = resultat_tmdb.get("title", "")
    if not se_ressemblent(titre_jpbox, titre_tmdb):
        return False

    # une suite ressemble beaucoup a son original : sans ce controle,
    # "Toy Story 5" repartait avec la fiche de "Toy Story", donc son
    # synopsis, son casting et son budget
    if numero_de_suite(titre_jpbox) != numero_de_suite(titre_tmdb):
        return False

    if annee_jpbox is None:
        return True  # pas d'annee dispo, on se base que sur le titre

    date_sortie = resultat_tmdb.get("release_date") or ""
    if len(date_sortie) < 4:
        return False

    annee_tmdb = int(date_sortie[:4])
    return abs(annee_tmdb - annee_jpbox) <= 1
