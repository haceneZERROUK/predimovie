# Notes IMDb, recuperees depuis le fichier public d'IMDb (pas de cle API)
import csv
import gzip
import io

import httpx

URL_NOTES_IMDB = "https://datasets.imdbws.com/title.ratings.tsv.gz"


def telecharger_notes_imdb() -> dict[str, float]:
    """Telecharge le fichier des notes et renvoie un dict
    {id_imdb: note}, ex {"tt1160419": 8.0}."""
    reponse = httpx.get(URL_NOTES_IMDB, timeout=30)
    reponse.raise_for_status()
    texte = gzip.decompress(reponse.content).decode("utf-8")
    return extraire_notes_imdb(texte)


def extraire_notes_imdb(texte_tsv: str) -> dict[str, float]:
    """Parse le TSV (colonnes tconst / averageRating / numVotes).
    A part pour les tests."""
    lecteur = csv.DictReader(io.StringIO(texte_tsv), delimiter="\t")
    return {ligne["tconst"]: float(ligne["averageRating"]) for ligne in lecteur}
