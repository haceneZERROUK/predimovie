# Fixture = extrait reel de blog.apify.com (2 articles hors-sujet pris sur
# la home, 2 articles sur le scraping pris sur la page de tag
# "anti-blocking"), sauvegarde pour ne pas dependre du reseau ni du site
# en direct - meme logique que data_engineering/tests/test_allocine.py.
from pathlib import Path

from veille.veille_scraping import (
    dedupliquer_par_url,
    est_article_sur_le_scraping,
    extraire_articles,
    filtrer_articles_scraping,
)

DOSSIER_FIXTURES = Path(__file__).parent / "fixtures"


def _lire_fixture(nom_fichier: str) -> str:
    return (DOSSIER_FIXTURES / nom_fichier).read_text(encoding="utf-8")


def test_extraire_articles_renvoie_les_4_articles_de_la_fixture():
    html = _lire_fixture("apify_blog.html")
    articles = extraire_articles(html)

    assert len(articles) == 4
    premier = articles[0]
    assert premier["titre"]
    assert premier["url"].startswith("https://blog.apify.com/")
    assert premier["date"]


def test_extraire_articles_urls_relatives_deviennent_absolues():
    html = _lire_fixture("apify_blog.html")
    articles = extraire_articles(html)

    for article in articles:
        assert article["url"].startswith("https://blog.apify.com/")


def test_est_article_sur_le_scraping_detecte_via_le_titre():
    article = {"titre": "How to scrape Facebook with Python", "extrait": "", "tags": []}
    assert est_article_sur_le_scraping(article) is True


def test_est_article_sur_le_scraping_detecte_via_un_tag_slug():
    # "Anti-blocking" (tiret) doit matcher "anti blocking" (espace) dans MOTS_CLES_SCRAPING
    article = {"titre": "Un titre neutre", "extrait": "", "tags": ["Anti-blocking"]}
    assert est_article_sur_le_scraping(article) is True


def test_est_article_sur_le_scraping_rejette_un_article_hors_sujet():
    article = {
        "titre": "Announcing MCP connectors",
        "extrait": "Apify Actors deviennent des automatisations completes.",
        "tags": ["Apify updates", "MCP", "AI agents"],
    }
    assert est_article_sur_le_scraping(article) is False


def test_dedupliquer_par_url_retire_les_doublons():
    articles = [
        {"url": "https://blog.apify.com/a/", "titre": "A"},
        {"url": "https://blog.apify.com/b/", "titre": "B"},
        {"url": "https://blog.apify.com/a/", "titre": "A (revu sur un autre tag)"},
    ]
    uniques = dedupliquer_par_url(articles)

    assert len(uniques) == 2
    assert [a["titre"] for a in uniques] == ["A", "B"]


def test_filtrer_articles_scraping_sur_la_fixture_reelle():
    # la fixture contient 2 articles sur le scraping (proxies, Facebook)
    # et 2 hors sujet (MCP connectors, builder spotlight)
    html = _lire_fixture("apify_blog.html")
    articles = extraire_articles(html)

    retenus = filtrer_articles_scraping(articles)

    assert len(retenus) == 2
    titres = [a["titre"] for a in retenus]
    assert any("scrape Facebook" in titre for titre in titres)
    assert not any("MCP" in titre for titre in titres)
