# Scraping du blog Apify (blog.apify.com) pour alimenter la page "Veille &
# actu secteur" avec des vrais articles frais, filtres sur la thematique
# scraping uniquement (le blog couvre aussi agents IA, MCP, market
# research... pas que du scraping). Declenche manuellement depuis la page
# Streamlit (bouton "Actualiser"), a un rythme hebdomadaire.
#
# Choix de Playwright ici (contrairement a data_engineering/allocine.py et
# jpbox.py qui utilisent httpx + BeautifulSoup) : le blog est en realite
# rendu cote serveur (verifie, pas besoin de JS pour voir les articles),
# donc httpx aurait suffi. Playwright est utilise volontairement pour
# demontrer l'outil sur un vrai cas d'usage, en complement du comparatif
# technique (page 1) - et parce qu'un blog peut passer en rendu cote
# client sans prevenir, contrairement a JPBOX/AlloCine dont le HTML est
# stable depuis le debut du projet.
import json
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL_BLOG = "https://blog.apify.com/"

# la home seule ne suffit pas : le blog parle surtout d'agents IA/MCP en ce
# moment, la home peut ne montrer aucun article de scraping une semaine
# donnee. On surveille en plus les pages de tags dediees au scraping pour
# une couverture hebdomadaire fiable (le filtre ci-dessous reste applique
# partout, au cas ou un tag contiendrait un article limite).
URLS_A_SURVEILLER = [
    URL_BLOG,
    "https://blog.apify.com/tag/anti-blocking/",
    "https://blog.apify.com/tag/scraping-libraries-and-frameworks/",
    "https://blog.apify.com/tag/web-automation-and-rpa/",
]

# mots-cles et bouts de tags (les tags Apify sont des slugs du type
# "anti-blocking", "web-automation-and-rpa") qui signalent un article sur
# le scraping. Les tirets des slugs sont remplaces par des espaces avant
# comparaison, donc "anti-blocking" matche bien sur "anti blocking".
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
    """Parse la liste d'articles d'une page du blog Apify (page d'accueil
    ou page de tag, meme structure). Renvoie titre/url/tags/auteur/date/
    extrait pour chaque article trouve."""
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
    """Un article est retenu s'il parle de scraping dans son titre, son
    extrait, ou l'un de ses tags - pas juste parce qu'il vient d'un blog
    qui parle *aussi* de scraping."""
    texte = " ".join([article["titre"], article["extrait"], *article["tags"]])
    texte = texte.lower().replace("-", " ")
    return any(mot_cle in texte for mot_cle in MOTS_CLES_SCRAPING)


def filtrer_articles_scraping(articles: list[dict]) -> list[dict]:
    return [article for article in articles if est_article_sur_le_scraping(article)]


def dedupliquer_par_url(articles: list[dict]) -> list[dict]:
    """Un meme article peut apparaitre sur plusieurs pages surveillees
    (home + plusieurs tags) : on ne le garde qu'une fois."""
    urls_vues = set()
    articles_uniques = []
    for article in articles:
        if article["url"] not in urls_vues:
            urls_vues.add(article["url"])
            articles_uniques.append(article)
    return articles_uniques


def scraper_articles_scraping(urls: list[str] = URLS_A_SURVEILLER) -> list[dict]:
    """Visite chaque page surveillee avec un vrai navigateur headless,
    dedoublonne et filtre sur la thematique scraping. Fonction non testee
    unitairement (pas de reseau/navigateur dans les tests) -
    extraire_articles(), filtrer_articles_scraping() et
    dedupliquer_par_url() portent toute la logique testable."""
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
    """Sauvegarde les articles avec la date de scraping, pour que la page
    Streamlit puisse afficher 'derniere actualisation le ...'."""
    contenu = {"date_maj": datetime.now(UTC).isoformat(), "articles": articles}
    chemin.write_text(json.dumps(contenu, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    articles = scraper_articles_scraping()
    ecrire_articles(articles)
    print(
        f"{len(articles)} article(s) sur le scraping trouve(s), "
        f"ecrit dans {CHEMIN_ARTICLES_PAR_DEFAUT}"
    )
