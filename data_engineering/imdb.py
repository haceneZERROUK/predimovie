# Récupère les notes IMDb via le fichier officiel et gratuit d'IMDb
# (pas besoin de clé API) : https://datasets.imdbws.com
import csv
import gzip
import io

import httpx

URL_NOTES_IMDB = "https://datasets.imdbws.com/title.ratings.tsv.gz"


def telecharger_notes_imdb() -> dict[str, float]:
    """Télécharge le fichier officiel des notes IMDb et renvoie un
    dictionnaire {identifiant_imdb: note_moyenne}, ex: {"tt1160419": 8.0}."""
    reponse = httpx.get(URL_NOTES_IMDB, timeout=30)
    reponse.raise_for_status()
    texte = gzip.decompress(reponse.content).decode("utf-8")
    return extraire_notes_imdb(texte)


def extraire_notes_imdb(texte_tsv: str) -> dict[str, float]:
    """Parse le contenu du fichier TSV (colonnes tconst / averageRating /
    numVotes). Séparé de telecharger_notes_imdb() pour être testé sans réseau."""
    lecteur = csv.DictReader(io.StringIO(texte_tsv), delimiter="\t")
    return {ligne["tconst"]: float(ligne["averageRating"]) for ligne in lecteur}
