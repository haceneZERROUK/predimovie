# Scraping du blog Apify pour alimenter la page "Veille & actu secteur",
# en ne gardant que les articles qui parlent de scraping. Lance a la main
# depuis Streamlit avec le bouton "Actualiser".
#
# Ici on utilise Playwright et pas httpx + BeautifulSoup comme dans
# data_engineering : pour montrer l'outil du comparatif technique, et
# parce qu'un blog peut passer en rendu JS du jour au lendemain.
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_BLOG = "https://blog.apify.com/"

# on ne regarde pas que la home : elle peut ne contenir aucun article de
# scraping une semaine donnee, donc on ajoute les pages de tags
URLS_A_SURVEILLER = [
    URL_BLOG,
    "https://blog.apify.com/tag/anti-blocking/",
    "https://blog.apify.com/tag/scraping-libraries-and-frameworks/",
    "https://blog.apify.com/tag/web-automation-and-rpa/",
]

# mots-cles qui indiquent un article sur le scraping. Les tags Apify sont
# des slugs avec des tirets, qu'on remplace par des espaces avant de
# comparer.
MOTS_CLES_SCRAPING = [
    "scraping",
    "scrape",
    "crawl",
    "crawlee",
    "anti blocking",
    "web automation",
    "proxy",
    "proxies",
]


def extraire_articles(html: str) -> list[dict]:
    """Parse la liste d'articles d'une page du blog (home ou page de tag,
    c'est la meme structure)."""
    soup = BeautifulSoup(html, "lxml")
    articles = []
    for carte in soup.select("article.post-card"):
        lien_titre = carte.select_one("h2.post-title a")
        if not lien_titre:
            continue
        auteur = carte.select_one(".author-name")
        date = carte.select_one("time.post-date")
        extrait = carte.select_one(".post-excerpt")
        articles.append(
            {
                "titre": lien_titre.get_text(strip=True),
                "url": urljoin(URL_BLOG, lien_titre["href"]),
                "tags": [tag.get_text(strip=True) for tag in carte.select("a.tag")],
                "auteur": auteur.get_text(strip=True) if auteur else None,
                "date": date["datetime"] if date and date.has_attr("datetime") else None,
                "extrait": extrait.get_text(strip=True) if extrait else "",
            }
        )
    return articles


def est_article_sur_le_scraping(article: dict) -> bool:
    """True si un mot-cle apparait dans le titre, l'extrait ou les tags."""
    texte = " ".join([article["titre"], article["extrait"], *article["tags"]])
    texte = texte.lower().replace("-", " ")
    return any(mot_cle in texte for mot_cle in MOTS_CLES_SCRAPING)


def filtrer_articles_scraping(articles: list[dict]) -> list[dict]:
    return [article for article in articles if est_article_sur_le_scraping(article)]


def dedupliquer_par_url(articles: list[dict]) -> list[dict]:
    """Un article peut sortir sur plusieurs pages, on ne le garde qu'une
    fois."""
    urls_vues = set()
    articles_uniques = []
    for article in articles:
        if article["url"] not in urls_vues:
            urls_vues.add(article["url"])
            articles_uniques.append(article)
    return articles_uniques


def scraper_articles_scraping(urls: list[str] = URLS_A_SURVEILLER) -> list[dict]:
    """Ouvre chaque page dans un navigateur headless, dedoublonne et
    filtre. Pas de test dessus, tout le reste du module est teste."""
    tous_les_articles = []
    with sync_playwright() as playwright:
        navigateur = playwright.chromium.launch()
        page = navigateur.new_page()
        for url in urls:
            page.goto(url, wait_until="domcontentloaded")
            tous_les_articles.extend(extraire_articles(page.content()))
        navigateur.close()
    return filtrer_articles_scraping(dedupliquer_par_url(tous_les_articles))


CHEMIN_ARTICLES_PAR_DEFAUT = Path(__file__).parent / "articles_veille.json"


def ecrire_articles(articles: list[dict], chemin: Path = CHEMIN_ARTICLES_PAR_DEFAUT) -> None:
    """Ecrit les articles dans le json, avec la date du scraping."""
    contenu = {"date_maj": datetime.now(UTC).isoformat(), "articles": articles}
    chemin.write_text(json.dumps(contenu, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    articles = scraper_articles_scraping()
    ecrire_articles(articles)
    print(
        f"{len(articles)} article(s) sur le scraping trouve(s), "
        f"ecrit dans {CHEMIN_ARTICLES_PAR_DEFAUT}"
    )
