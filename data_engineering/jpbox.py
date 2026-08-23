# Scraper pour https://www.jpbox-office.com : le site qui donne les
# entrées (fréquentation) des films en salle, en France et à l'étranger.
import re
import time

import httpx
from bs4 import BeautifulSoup

from data_engineering.config import (
    JPBOX_BASE_URL,
    JPBOX_DELAI_ENTRE_REQUETES,
    JPBOX_USER_AGENT,
    JPBOX_VUE_FRANCE,
)

EN_TETES = {"User-Agent": JPBOX_USER_AGENT}


def _telecharger_page(url: str) -> str:
    """Télécharge une page JPBOX et attend un peu avant de continuer,
    pour ne pas trop solliciter le site (voir JPBOX_DELAI_ENTRE_REQUETES)."""
    reponse = httpx.get(url, headers=EN_TETES, timeout=15)
    reponse.raise_for_status()
    time.sleep(JPBOX_DELAI_ENTRE_REQUETES)
    return reponse.text


def _texte_vers_nombre(texte: str) -> int | None:
    """Convertit un texte comme '1 618 366' en nombre entier 1618366."""
    chiffres = re.sub(r"[^\d]", "", texte or "")
    return int(chiffres) if chiffres else None


def _lire_cellule_titre(cellule) -> dict:
    """Lit la cellule d'une ligne du classement qui contient le titre,
    l'année, le lien vers la fiche du film et le titre original."""
    h3 = cellule.find("h3")
    lien = h3.find("a")

    # certains films n'ont pas encore de fiche JPBOX : pas de lien, pas d'année
    if lien is None:
        titre = h3.get_text(strip=True)
        return {
            "id_jpbox": None,
            "titre_francais": titre,
            "titre_original": titre,
            "annee_sortie": None,
        }

    titre_et_annee = lien.get_text(strip=True)

    # le titre français se termine par "(2026)" par exemple
    match = re.match(r"(.+)\s\((\d{4})\)$", titre_et_annee)
    if match:
        titre_francais, annee_sortie = match.group(1), int(match.group(2))
    else:
        titre_francais, annee_sortie = titre_et_annee, None

    id_match = re.search(r"id=(\d+)", lien["href"])
    id_jpbox = int(id_match.group(1)) if id_match else None

    # le texte juste après le titre (avant le premier <br/>) = titre original
    titre_original = h3.next_sibling
    titre_original = titre_original.strip() if titre_original else ""

    return {
        "id_jpbox": id_jpbox,
        "titre_francais": titre_francais,
        "titre_original": titre_original or titre_francais,
        "annee_sortie": annee_sortie,
    }


def classement_hebdo(idsem: int, vue: int) -> list[dict]:
    """Récupère le classement box-office d'une semaine donnée.
    idsem = identifiant de semaine JPBOX, vue = code pays (France, etc.)."""
    url = f"{JPBOX_BASE_URL}/v9_tophebdo.php?view={vue}&idsem={idsem}"
    html = _telecharger_page(url)
    return extraire_classement(html)


def extraire_classement(html: str) -> list[dict]:
    """Parse le HTML d'une page de classement hebdomadaire.
    Séparé de classement_hebdo() pour pouvoir être testé sans réseau."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="tablesmall5")
    if table is None:
        return []

    films = []
    for ligne in table.find_all("tr"):
        cellules = ligne.find_all("td")
        if len(cellules) < 10:
            continue  # ligne d'en-tête ou ligne incomplète : on l'ignore

        film = _lire_cellule_titre(cellules[2])
        film["semaine_exploitation"] = _texte_vers_nombre(cellules[3].get_text())
        film["entrees_semaine"] = _texte_vers_nombre(cellules[4].get_text())
        films.append(film)

    return films


def _lire_lien_calendrier(lien) -> dict:
    """Lit un lien vers une fiche film sur la page calendrier (titre +
    annee sont dans le texte du lien, pas besoin d'aller sur la fiche).

    Le lien contient parfois le titre francais puis, apres un <br/>, le
    titre original (ex: "Tad l'explorateur...<br/>Tadeo Jones..."). On ne
    garde que la premiere ligne (titre francais)."""
    premiere_ligne = lien.find(string=True, recursive=False)
    titre_et_annee = premiere_ligne.strip() if premiere_ligne else lien.get_text(strip=True)

    match = re.match(r"(.+)\s\((\d{4})\)$", titre_et_annee)
    if match:
        titre_francais, annee_sortie = match.group(1), int(match.group(2))
    else:
        titre_francais, annee_sortie = titre_et_annee, None

    id_match = re.search(r"id=(\d+)", lien["href"])
    id_jpbox = int(id_match.group(1)) if id_match else None

    return {
        "id_jpbox": id_jpbox,
        "titre_francais": titre_francais,
        "annee_sortie": annee_sortie,
    }


def films_du_calendrier(date_sortie, vue: int = JPBOX_VUE_FRANCE) -> list[dict]:
    """Recupere TOUS les films qui sortent a une date donnee, via le
    calendrier des sorties JPBOX (v9_avenir.php). Contrairement a la page
    d'accueil qui ne met en avant qu'une poignee de grosses sorties, cette
    page liste vraiment tous les films prevus ce jour-la."""
    url = f"{JPBOX_BASE_URL}/v9_avenir.php?view={vue}&date={date_sortie.isoformat()}&fixe=1"
    html = _telecharger_page(url)
    return extraire_films_du_calendrier(html)


def extraire_films_du_calendrier(html: str) -> list[dict]:
    """Parse le HTML de la page calendrier des sorties.
    Separe de films_du_calendrier() pour pouvoir etre teste sans reseau."""
    soup = BeautifulSoup(html, "lxml")

    films = []
    ids_deja_vus = set()
    for lien in soup.find_all("a", href=re.compile(r"^fichfilm\.php\?id=\d+")):
        film = _lire_lien_calendrier(lien)
        if film["id_jpbox"] in ids_deja_vus:
            continue  # le meme film peut avoir plusieurs liens sur la page
        ids_deja_vus.add(film["id_jpbox"])
        films.append(film)
    return films
