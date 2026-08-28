import json
from datetime import UTC, datetime
from pathlib import Path

import streamlit as st

from veille.veille_scraping import ecrire_articles, scraper_articles_scraping

st.set_page_config(
    page_title="Veille & actu secteur - Veille scraping", page_icon="🕵️", layout="wide"
)

st.title("Veille & actu secteur du scraping")
st.caption("Sources citees pour chaque partie - pas de contenu invente.")

st.header("Derniers articles collectes")
st.markdown(
    "Scrape [blog.apify.com](https://blog.apify.com/) (Playwright) et ne garde que "
    "les articles sur le scraping (le blog couvre aussi agents IA, MCP, etc.). "
    "Actualisation manuelle, a un rythme hebdomadaire."
)

CHEMIN_ARTICLES = Path(__file__).parent.parent / "articles_veille.json"

if st.button("🔄 Actualiser la veille"):
    with st.spinner("Scraping du blog en cours (Playwright, ~15s)..."):
        articles = scraper_articles_scraping()
        ecrire_articles(articles, CHEMIN_ARTICLES)
    st.rerun()

if CHEMIN_ARTICLES.exists():
    donnees = json.loads(CHEMIN_ARTICLES.read_text())
    date_maj = datetime.fromisoformat(donnees["date_maj"]).astimezone(UTC)
    st.caption(f"Derniere actualisation : {date_maj:%d/%m/%Y %H:%M} UTC")
    if donnees["articles"]:
        for article in donnees["articles"]:
            st.markdown(
                f"- **[{article['titre']}]({article['url']})** "
                f"— {article['auteur'] or 'auteur inconnu'}, {article['date'] or 'date inconnue'}"
            )
    else:
        st.info("Aucun article sur le scraping lors du dernier passage (autres sujets publies).")
else:
    st.info("Pas encore de scraping execute - clique sur 'Actualiser la veille' ci-dessus.")

st.markdown("---")

# url trop longue pour tenir sur une ligne de markdown sans depasser 100 caracteres
url_hiq = "https://calawyers.org/privacy-law/ninth-circuit-holds-data-scraping-is-legal-in-hiq-v-linkedin/"  # noqa: E501

st.header("La course anti-bot s'est durcie")
st.markdown("""
Les gros acteurs anti-bot (**Cloudflare**, **DataDome**, **PerimeterX/HUMAN Security**)
ne se contentent plus de bloquer une IP suspecte : DataDome fait tourner plus de
**85 000 modeles de machine learning specifiques par client**, et le fingerprinting
(empreinte TLS, comportement de la souris, timing des requetes) a rendu les vieilles
techniques (rotation d'IP + faux User-Agent) largement insuffisantes seules.

**Fait marquant** : Cloudflare bloque le scraping par IA **par defaut** depuis
juillet 2025.

*Source : [finedata.ai — Anti-Bot Detection 2026](https://finedata.ai/blog/anti-bot-detection-2026/)*
""")

st.header("Le trafic de bots IA a explose")
st.markdown("""
Entre janvier et decembre 2025, le trafic de bots IA a augmente de **+187%**,
contre +3,1% pour le trafic humain. Les bots depassent desormais le trafic humain
sur le web mondial pour la 2e annee consecutive (**53%** du trafic total, dont
**40%** de "bad bots").

*Source : [Coronium.io — The AI Crawler War 2026](https://www.coronium.io/blog/ai-web-scraping-crawler-war-2026)*
""")

st.header("Le flou juridique persiste (cas hiQ vs LinkedIn)")
st.markdown(f"""
L'affaire **hiQ Labs vs LinkedIn** reste la reference americaine. La cour d'appel
du 9e circuit avait juge que scraper des donnees **publiques** n'est pas un crime
au sens du CFAA (la loi federale americaine sur la fraude informatique). Mais le
litige a rebondi sur un autre terrain : la violation des conditions d'utilisation
(ToS) et l'usage de faux comptes par hiQ pour contourner les restrictions —
LinkedIn a fini par gagner sur ce point.

**A retenir** : scraper des donnees publiques n'est pas automatiquement illegal,
mais violer les CGU d'un site ou usurper des comptes l'est. La frontiere reste
fixee par la jurisprudence, pas par une loi claire et unique.

*Sources : [California Lawyers Association]({url_hiq}) ·
[Blog Apify](https://blog.apify.com/hiq-v-linkedin/) ·
[Nubela — Is Scraping Legal in 2026](https://nubela.co/blog/is-scraping-linkedin-legal-in-2026/)*
""")

st.header("Playwright integre de l'IA")
st.markdown("""
Playwright (Microsoft), devenu la reference pour les sites charges en JavaScript,
a gagne en 2026 des fonctions IA : des **Test Agents** qui generent et reparent des
tests automatiquement, et **Playwright MCP**, ou un agent IA pilote un navigateur
via des "accessibility snapshots" plutot que des captures d'ecran.

*Source : [ThinkSys — Playwright Features 2026](https://thinksys.com/qa-testing/playwright-features/)*
""")

st.markdown("---")
st.subheader("Le lien avec Predimovie")
st.markdown("""
JPBOX (une des 2 sources scrapees par Predimovie) a publiquement signale sur son
site des abus de bots IA — exactement la tendance "AI Crawler War" decrite plus
haut. La reponse de Predimovie (User-Agent explicite, delai de politesse entre
requetes, pas de contournement agressif) va dans le sens des bonnes pratiques
recommandees face a cette pression montante, plutot que dans une course a
l'armement anti-anti-bot.
""")
