# Extrait 3 mots-cles du synopsis des films avec l'API Claude
import httpx
from sqlalchemy.orm import Session

from data_engineering.config import SYNOPSIS_ENRICHMENT_API_KEY
from database.models import Oeuvre

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODELE = "claude-haiku-4-5-20251001"
LONGUEUR_MIN_SYNOPSIS = 50  # en dessous le synopsis est trop court pour etre utile

PROMPT = (
    "Voici le synopsis d'un film :\n\n"
    "{synopsis}\n\n"
    "Reponds uniquement avec exactement 3 mots-cles qui resument ce film, "
    "en francais, separes par des virgules. Pas de phrase, pas d'introduction, "
    "juste les 3 mots-cles. juste un mot de 50 caractere maximum"
)


def _parser_reponse_llm(texte: str) -> list[str]:
    """Coupe la reponse sur les virgules : 3 mots-cles max, tronques a 100
    caracteres (la taille de la colonne en base)."""
    return [m.strip()[:100] for m in texte.split(",") if m.strip()][:3]


def extraire_mots_cles(synopsis: str) -> list[str]:
    reponse = httpx.post(
        ANTHROPIC_URL,
        headers={
            "x-api-key": SYNOPSIS_ENRICHMENT_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODELE,
            "max_tokens": 100,
            "messages": [{"role": "user", "content": PROMPT.format(synopsis=synopsis)}],
        },
        timeout=30,
    )
    reponse.raise_for_status()
    return _parser_reponse_llm(reponse.json()["content"][0]["text"])


def enrichir_les_films_sans_mots_cles(session: Session) -> int:
    """Passe sur les films qui ont un synopsis mais pas encore de mots-cles
    et les remplit. Renvoie le nombre de films traites."""
    films = (
        session.query(Oeuvre)
        .filter(Oeuvre.synopsis.isnot(None))
        .filter(Oeuvre.mot_cle_1.is_(None))
        .all()
    )

    nb = 0
    for film in films:
        if not film.synopsis or len(film.synopsis) <= LONGUEUR_MIN_SYNOPSIS:
            continue
        mots = extraire_mots_cles(film.synopsis)
        film.mot_cle_1 = mots[0] if len(mots) > 0 else None
        film.mot_cle_2 = mots[1] if len(mots) > 1 else None
        film.mot_cle_3 = mots[2] if len(mots) > 2 else None
        nb += 1

    session.commit()
    return nb


if __name__ == "__main__":
    from database.base import SessionLocal

    session = SessionLocal()
    try:
        nb = enrichir_les_films_sans_mots_cles(session)
        print(f"{nb} films mis a jour avec des mots-cles")
    finally:
        session.close()
