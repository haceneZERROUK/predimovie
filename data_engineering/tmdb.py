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


def get_dates_sortie_par_pays(tmdb_id: int) -> list[dict]:
    """Récupère les dates de sortie officielles, pays par pays. Le champ
    "release_date" de get_details_film() n'est pas forcement la date
    française (souvent la date US) : on utilise ça pour la vraie date FR."""
    params = {"api_key": TMDB_API_KEY}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/release_dates", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json().get("results", [])


def date_sortie_france(resultats_par_pays: list[dict]) -> str | None:
    """Cherche la date de sortie en salle (type 3 = "Theatrical") en
    France dans le resultat de get_dates_sortie_par_pays().
    Renvoie None si TMDB n'a pas encore de date FR pour ce film."""
    for pays in resultats_par_pays:
        if pays.get("iso_3166_1") != "FR":
            continue
        dates_salle = sorted(
            rd["release_date"][:10] for rd in pays.get("release_dates", []) if rd.get("type") == 3
        )
        return dates_salle[0] if dates_salle else None
    return None
