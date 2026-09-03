# Appels a l'API TMDB (synopsis, genres, casting, dates de sortie)
import httpx

from data_engineering.config import TMDB_API_KEY, TMDB_BASE_URL


def rechercher_films(titre: str, annee: int | None = None) -> list[dict]:
    """Cherche un film par titre, et par annee si on l'a. Renvoie tous les
    resultats, le bon n'est pas forcement le premier."""
    params = {"api_key": TMDB_API_KEY, "query": titre, "language": "fr-FR"}
    if annee:
        params["year"] = annee
    reponse = httpx.get(f"{TMDB_BASE_URL}/search/movie", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json().get("results", [])


def trouver_par_imdb_id(imdb_id: str) -> dict | None:
    """Retrouve un film TMDB avec son id IMDb."""
    params = {"api_key": TMDB_API_KEY, "external_source": "imdb_id"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/find/{imdb_id}", params=params, timeout=10)
    reponse.raise_for_status()
    resultats = reponse.json().get("movie_results", [])
    return resultats[0] if resultats else None


def get_details_film(tmdb_id: int) -> dict:
    """Fiche complete du film : synopsis, genres, budget, societes de prod..."""
    params = {"api_key": TMDB_API_KEY, "language": "fr-FR"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json()


def get_casting_film(tmdb_id: int) -> dict:
    """Casting du film : les acteurs (cast) et l'equipe technique (crew),
    ou on retrouve le realisateur."""
    params = {"api_key": TMDB_API_KEY, "language": "fr-FR"}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json()


def get_dates_sortie_par_pays(tmdb_id: int) -> list[dict]:
    """Les dates de sortie du film pays par pays."""
    params = {"api_key": TMDB_API_KEY}
    reponse = httpx.get(f"{TMDB_BASE_URL}/movie/{tmdb_id}/release_dates", params=params, timeout=10)
    reponse.raise_for_status()
    return reponse.json().get("results", [])


def date_sortie_france(resultats_par_pays: list[dict]) -> str | None:
    """Prend la date de sortie en salle en France (type 3 = "Theatrical")
    dans ce que renvoie get_dates_sortie_par_pays(). None s'il n'y en a pas."""
    for pays in resultats_par_pays:
        if pays.get("iso_3166_1") != "FR":
            continue
        dates_salle = sorted(
            rd["release_date"][:10] for rd in pays.get("release_dates", []) if rd.get("type") == 3
        )
        return dates_salle[0] if dates_salle else None
    return None
