# Accueil de la veille techno. Les autres pages sont dans veille/pages/,
# Streamlit fait la nav tout seul a partir de ce dossier.
import streamlit as st

st.set_page_config(page_title="Veille - Scraping", page_icon="🕵️", layout="wide")

st.title("Veille technologique : le web scraping")
st.caption("Predimovie - certification Simplon")

st.markdown("""
Cette veille porte sur le **web scraping**, la technique utilisee dans Predimovie
pour recuperer les sorties cinema et les entrees box-office (JPBOX, AlloCine, TMDB).

Deux volets :

- **Comparatif technique** : BeautifulSoup, Scrapy, Selenium, Playwright — quand utiliser
  quoi, et pourquoi Predimovie s'appuie sur BeautifulSoup.
- **Veille & actu secteur** : anti-bot, IA, cadre legal — ce qui bouge en ce moment
  dans le scraping.

Utilise le menu a gauche pour naviguer entre les pages.
""")
