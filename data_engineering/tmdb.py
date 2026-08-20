# Petites fonctions pour interroger l'API TMDB (https://www.themoviedb.org).
# TMDB nous donne le synopsis, les genres, le casting et le réalisateur
# d'un film : des informations plus riches et plus fiables à récupérer
# ici qu'en scrapant du HTML.
import httpx

from data_engineering.config import TMDB_API_KEY, TMDB_BASE_URL


def rechercher_films(titre: str, annee: int | None = None) -> list[dict]:
    """Cherche un film sur TMDB par titre (+ année si on la connaît).
    Retourne tous les résultats : le bon film n'est pas toujours le premier
    (ex: un titre court comme "Who" est noyé parmi des films plus connus)."""
    params = {"api_key": TMDB_API_KEY, "query": titre, "language": "fr-FR"}
    if annee:
        params["year"] = annee
    reponse = httpx.get(f"{TMDB_BASE_URL}/search/movie", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json().get("results", [])


def trouver_par_imdb_id(imdb_id: str) -> dict | None:
    """Retrouve un film TMDB à partir de son identifiant IMDb.
    C'est une jointure exacte, plus fiable qu'une recherche par titre."""
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/find/{imdb_id}", params=params, timeout=10)
    reponse.raise_for_status()
    resultats = reponse.json().get("movie_results", [])
    return resultats[0] if resultats else None


def get_details_film(tmdb_id: int) -> dict:
    """Récupère le synopsis, les genres et les sociétés de production."""
    params = {"api_key": TMDB_API_KEY, "language": "fr-FR"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json()


def get_casting_film(tmdb_id: int) -> dict:
    """Récupère la liste des acteurs (cast) et de l'équipe technique (crew),
    dont le réalisateur fait partie."""
    params = {"api_key": TMDB_API_KEY, "language": "fr-FR"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json()
