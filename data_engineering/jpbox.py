# Scraping de jpbox-office.com (entrees des films en salle)
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
    """Telecharge une page et attend un peu apres, pour ne pas surcharger
    le site."""
    reponse = httpx.get(url, headers=EN_TETES, timeout=15)
    reponse.raise_for_status()
    time.sleep(JPBOX_DELAI_ENTRE_REQUETES)
    return reponse.text


def _texte_vers_nombre(texte: str) -> int | None:
    """'1 618 366' -> 1618366. None si pas de chiffre dedans."""
    chiffres = re.sub(r"[^\d]", "", texte or "")
    return int(chiffres) if chiffres else None


def _lire_cellule_titre(cellule) -> dict:
    """Lit la cellule du classement qui contient le titre, l'annee, le lien
    vers la fiche et le titre original."""
    h3 = cellule.find("h3")
    lien = h3.find("a")

    # certains films n'ont pas encore de fiche : pas de lien donc pas d'annee
    if lien is None:
        titre = h3.get_text(strip=True)
        return {
            "id_jpbox": None,
            "titre_francais": titre,
            "titre_original": titre,
            "annee_sortie": None,
        }

    titre_et_annee = lien.get_text(strip=True)

    # le titre se termine par l'annee entre parentheses, ex "Titre (2026)"
    match = re.match(r"(.+)\s\((\d{4})\)$", titre_et_annee)
    if match:
        titre_francais, annee_sortie = match.group(1), int(match.group(2))
    else:
        titre_francais, annee_sortie = titre_et_annee, None

    id_match = re.search(r"id=(\d+)", lien["href"])
    id_jpbox = int(id_match.group(1)) if id_match else None

    # le texte juste apres le <h3> c'est le titre original
    titre_original = h3.next_sibling
    titre_original = titre_original.strip() if titre_original else ""

    return {
        "id_jpbox": id_jpbox,
        "titre_francais": titre_francais,
        "titre_original": titre_original or titre_francais,
        "annee_sortie": annee_sortie,
    }


def classement_hebdo(idsem: int, vue: int) -> list[dict]:
    """Classement box-office d'une semaine. idsem = numero de semaine JPBOX,
    vue = code du pays."""
    url = f"{JPBOX_BASE_URL}/v9_tophebdo.php?view={vue}&idsem={idsem}"
    html = _telecharger_page(url)
    return extraire_classement(html)


def extraire_classement(html: str) -> list[dict]:
    """Parse le HTML d'un classement hebdo. A part de classement_hebdo()
    pour pouvoir le tester sans reseau."""
    soup = BeautifulSoup(html, "lxml")
    table = soup.find("table", class_="tablesmall5")
    if table is None:
        return []

    films = []
    for ligne in table.find_all("tr"):
        cellules = ligne.find_all("td")
        if len(cellules) < 10:
            continue  # en-tete ou ligne incomplete

        film = _lire_cellule_titre(cellules[2])
        film["semaine_exploitation"] = _texte_vers_nombre(cellules[3].get_text())
        film["entrees_semaine"] = _texte_vers_nombre(cellules[4].get_text())
        films.append(film)

    return films


def nb_salles_premiere_semaine(id_jpbox: int) -> int | None:
    """Nombre de salles en 1ere semaine, lu sur l'onglet "Resultats France"
    de la fiche du film (view=2)."""
    url = f"{JPBOX_BASE_URL}/fichfilm.php?id={id_jpbox}&view=2"
    html = _telecharger_page(url)
    return extraire_nb_salles_semaine1(html)


def extraire_nb_salles_semaine1(html: str) -> int | None:
    """Parse le HTML de l'onglet "Resultats France". A part pour les tests."""
    soup = BeautifulSoup(html, "lxml")
    for table in soup.find_all("table", class_="tablesmall5"):
        lignes = table.find_all("tr")
        if len(lignes) < 2:
            continue
        cellules = lignes[1].find_all("td")  # 1ere ligne de data = semaine 1
        if len(cellules) < 6:
            continue
        return _texte_vers_nombre(cellules[5].get_text())
    return None


def _lire_lien_calendrier(lien) -> dict:
    """Lit un lien de la page calendrier : le titre et l'annee sont dans le
    texte du lien. Quand il y a le titre original apres un <br/> on garde
    juste la premiere ligne."""
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
    """Tous les films qui sortent a une date donnee, pris sur le calendrier
    des sorties (v9_avenir.php)."""
    url = f"{JPBOX_BASE_URL}/v9_avenir.php?view={vue}&date={date_sortie.isoformat()}&fixe=1"
    html = _telecharger_page(url)
    return extraire_films_du_calendrier(html)


def extraire_films_du_calendrier(html: str) -> list[dict]:
    """Parse le HTML du calendrier des sorties. A part pour les tests."""
    soup = BeautifulSoup(html, "lxml")

    films = []
    ids_deja_vus = set()
    for lien in soup.find_all("a", href=re.compile(r"^fichfilm\.php\?id=\d+")):
        film = _lire_lien_calendrier(lien)
        if film["id_jpbox"] in ids_deja_vus:
            continue  # un film peut avoir plusieurs liens sur la page
        ids_deja_vus.add(film["id_jpbox"])
        films.append(film)
    return films
