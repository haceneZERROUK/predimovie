import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Comparatif technique - Veille scraping", page_icon="🕵️", layout="wide"
)

st.title("Comparatif technique des outils de scraping")

st.markdown("""
4 outils Python reviennent tout le temps des qu'on parle de scraping. Ils ne servent
pas au meme usage : le vrai critere de choix, c'est **est-ce que le site rend son
contenu en HTML des la reponse serveur, ou est-ce qu'il faut executer du JavaScript
pour le voir apparaitre** (SPA React/Vue, contenu charge en AJAX, etc.).
""")

donnees = {
    "Outil": ["BeautifulSoup (bs4)", "Scrapy", "Selenium", "Playwright"],
    "Type": [
        "Bibliotheque de parsing HTML/XML",
        "Framework de crawling complet",
        "Automatisation de navigateur",
        "Automatisation de navigateur",
    ],
    "Execute le JS ?": ["Non", "Non (par defaut)", "Oui", "Oui"],
    "Vitesse": [
        "Rapide (pas de navigateur)",
        "Rapide, + async natif",
        "Lent (navigateur reel)",
        "Plus rapide que Selenium",
    ],
    "Courbe d'apprentissage": ["Tres simple", "Moyenne (son propre framework)", "Simple", "Simple"],
    "Cas d'usage typique": [
        "Parser du HTML deja recupere (avec httpx/requests)",
        "Crawl a grande echelle, sites multiples, pipelines de donnees",
        "Sites avec JS, tests end-to-end, formulaires interactifs",
        "Comme Selenium, plus moderne et plus rapide (multi-navigateurs)",
    ],
}
df = pd.DataFrame(donnees)
st.dataframe(df, hide_index=True, use_container_width=True)

st.markdown("---")
st.header("Pourquoi Predimovie utilise BeautifulSoup")

st.markdown("""
Le scraper de Predimovie (`data_engineering/jpbox.py`, `allocine.py`) recupere les
pages avec `httpx`, puis les parse avec **BeautifulSoup + lxml**. Pas de Scrapy, pas
de navigateur automatise. 3 raisons concretes :

1. **JPBOX et AlloCine sont du HTML classique cote serveur** — pas de SPA, pas de
   contenu charge en JS. Un simple `GET` suffit, un navigateur headless
   (Selenium/Playwright) n'apporterait rien, juste du temps CPU et de la memoire en plus.
2. **Le volume est petit et le rythme est faible** (un scrape par semaine, quelques
   dizaines de films). Scrapy est concu pour du crawl a grande echelle avec pipelines,
   middlewares, retries automatiques... utile a partir d'un vrai gros volume, pas ici.
3. **JPBOX a publiquement signale des abus de bots IA** sur son site : la reponse a ete
   de rester discret (`User-Agent` explicite, delai entre requetes), pas d'aller plus
   vite avec un outil plus lourd.

BeautifulSoup + httpx, c'est le plus simple qui marche pour ce besoin — pas la peine
d'ajouter un framework de crawling pour 2 sites scrapes une fois par semaine.
""")
