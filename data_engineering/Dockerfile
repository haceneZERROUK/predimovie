FROM python:3.11-slim

WORKDIR /app

# On copie tout le projet car le scraper importe le code de database/ et
# (pour la tache hebdomadaire) le sous-modele salles dans ml/
COPY pyproject.toml README.md ./
COPY data_engineering ./data_engineering
COPY database ./database
COPY ml ./ml

RUN pip install --no-cache-dir .

EXPOSE 8001

CMD ["uvicorn", "data_engineering.main:app", "--host", "0.0.0.0", "--port", "8001"]
