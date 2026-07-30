# Predimovie

Système de recommandation de films — projet de certification Simplon.

## Stack

- **Data Engineering (C1-C3)** : pipeline ETL Python orchestré par N8n (extraction/enrichissement JPBOX).
- **Base de données (C4)** : PostgreSQL, modèle relationnel géré via SQLAlchemy + Alembic (`database/`).
- **Back-end & IA (C5, C9)** : API FastAPI, modèle Scikit-Learn suivi par MLflow.
- **Proof of Concept (C8)** : prototype Streamlit.
- **Front-end (C17)** : application cliente Django.
- **MLOps & CI/CD (C11, C12, C18-C21)** : GitHub Actions, ruff/black, semantic-release, monitoring Grafana.

## Démarrage

```bash
cp .env.example .env
uv sync --extra dev
docker compose up -d
```

## Migrations de base de données

```bash
uv run alembic -c database/alembic.ini revision --autogenerate -m "message"
uv run alembic -c database/alembic.ini upgrade head
```
