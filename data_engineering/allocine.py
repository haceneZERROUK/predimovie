# Scraping d'allocine.fr, pour completer les sorties trouvees sur JPBOX
# (JPBOX ne liste que les films avec un suivi box-office)
import re
import time

import httpx
from bs4 import BeautifulSoup

from data_engineering.config import (
    ALLOCINE_BASE_URL,
    ALLOCINE_DELAI_ENTRE_REQUETES,
    ALLOCINE_USER_AGENT,
)

EN_TETES = {"User-Agent": ALLOCINE_USER_AGENT}


def _telecharger_page(url: str) -> str:
    """Telecharge une page et attend un peu apres, comme pour JPBOX."""
    reponse = httpx.get(url, headers=EN_TETES, timeout=15)
    reponse.raise_for_status()
    time.sleep(ALLOCINE_DELAI_ENTRE_REQUETES)
    return reponse.text


def films_de_la_semaine(date_sortie) -> list[dict]:
    """Les films qui sortent la semaine d'une date donnee. L'agenda
    AlloCine est decoupe par semaine, du mercredi au mardi."""
    url = f"{ALLOCINE_BASE_URL}/film/agenda/sem-{date_sortie.isoformat()}/"
    html = _telecharger_page(url)
    return extraire_films_de_la_semaine(html)


def extraire_films_de_la_semaine(html: str) -> list[dict]:
    """Parse le HTML de la page agenda. A part pour les tests."""
    soup = BeautifulSoup(html, "lxml")

    films = []
    ids_deja_vus = set()
    for li in soup.find_all("li", class_="mdl"):
        lien = li.find("a", href=re.compile(r"/film/fichefilm_gen_cfilm=\d+\.html"))
        if lien is None:
            continue

        id_match = re.search(r"cfilm=(\d+)", lien["href"])
        id_allocine = int(id_match.group(1)) if id_match else None
        if id_allocine is None or id_allocine in ids_deja_vus:
            continue
        ids_deja_vus.add(id_allocine)

        titre_tag = li.find(attrs={"title": True})
        titre_francais = titre_tag.get("title") if titre_tag else lien.get_text(strip=True)
        if not titre_francais:
            continue

        films.append({"id_allocine": id_allocine, "titre_francais": titre_francais})

    return films
