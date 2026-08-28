FROM python:3.11-slim

WORKDIR /app

# le POC veille est autonome, pas besoin des autres packages du projet
COPY pyproject.toml README.md ./
COPY veille ./veille

RUN pip install --no-cache-dir ".[veille]"
# navigateur pour le scraping de veille (veille_scraping.py) - --with-deps
# installe aussi les librairies systeme necessaires, plus lourd que le
# BeautifulSoup+httpx utilise par data_engineering/ mais c'est assume
# (cf comparatif technique, page 1 du POC)
RUN playwright install --with-deps chromium

EXPOSE 8501

CMD ["streamlit", "run", "veille/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
