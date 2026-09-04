# Predimovie

Predimovie estime le nombre d'entrées qu'un film fera pendant sa **première semaine
d'exploitation**, pour aider les petits cinémas indépendants à décider quoi programmer.
Ce n'est pas une application de recommandation grand public : c'est un outil d'aide à la
programmation, destiné aux exploitants.

Projet de certification Simplon — Développeur en intelligence artificielle (RNCP37827).

## Tester l'application

L'application Django est déployée et accessible ici :

**https://frontend-production-ec9eb.up.railway.app**

Un compte de démonstration est mis à disposition pour la parcourir :

| | |
|---|---|
| Identifiant | `cine-test` |
| Mot de passe | `Cinema123` |

Ce compte a le rôle `CINEMA`. Il donne accès à l'accueil et au **Top 10 des sorties de la
semaine**, avec la prédiction d'entrées calculée pour chaque film. Les pages
d'administration (historique prédit/réel, monitoring, gestion des comptes) sont réservées
au rôle `ADMIN` et resteront inaccessibles, tout comme la relance des prédictions et le
réentraînement du modèle.

## L'API

| Ressource | Adresse |
|---|---|
| Documentation Swagger | https://backend-production-6e90.up.railway.app/docs |
| Schéma OpenAPI | https://backend-production-6e90.up.railway.app/openapi.json |
| État de santé | https://backend-production-6e90.up.railway.app/health |
| Métriques Prometheus | https://backend-production-6e90.up.railway.app/metrics |

Les routes de prédiction demandent un jeton JWT, obtenu via `POST /auth/login` avec les
identifiants ci-dessus.

## Ce qui tourne où

Seuls le front, l'API et les deux tâches planifiées sont déployés. Le reste s'exécute en
local via `docker compose`.

| Brique | En ligne | En local |
|---|---|---|
| Front Django | ✅ Railway | `localhost:8080` |
| API FastAPI | ✅ Railway | `localhost:8000` |
| Base PostgreSQL | ✅ Supabase | `localhost:5432` |
| Collecte hebdomadaire | ✅ cron Railway, lundi 6h UTC | — |
| Réentraînement mensuel | ✅ cron Railway, le 1er à 6h UTC | — |
| Veille (PoC Streamlit) | — | `localhost:8501` |
| Scraper | — | `localhost:8001` |
| MLflow | — | `localhost:5000` |
| Prometheus | — | `localhost:9090` |
| Grafana | — | `localhost:3000` |

## Stack

- **Collecte des données (C1-C3)** : scraping JPBOX-Office et AlloCiné, métadonnées TMDB,
  notes IMDb, rapprochement des titres par similarité floue (`data_engineering/`).
- **Base de données (C4-C5)** : PostgreSQL, SQLAlchemy et migrations Alembic (`database/`).
- **Modèle (C6-C9)** : scikit-learn, XGBoost et CatBoost, suivi des entraînements sous
  MLflow, sous-modèle d'estimation du nombre de salles (`ml/`).
- **API (C9-C13)** : FastAPI, authentification JWT, métriques exposées au format
  Prometheus (`backend/`).
- **Application (C14-C19)** : front Django appelant l'API (`frontend_django/`).
- **Veille (C6-C8)** : PoC Streamlit, scraping du blog Apify avec Playwright (`veille/`).
- **Automatisation et CI/CD (C18-C21)** : GitHub Actions (lint, tests, publication des
  images), cron jobs Railway, tableaux de bord Grafana (`monitoring/`).

## Démarrage en local

```bash
cp .env.example .env      # à compléter avec vos propres clés
uv sync --extra dev
docker compose up -d
```

Pour ne lancer que le monitoring :

```bash
docker compose up -d postgres backend prometheus grafana
```

## Tests

```bash
pytest                    # nécessite une base predimovie_test accessible
ruff check . && black --check .
```

## Migrations de base de données

```bash
uv run alembic -c database/alembic.ini revision --autogenerate -m "message"
uv run alembic -c database/alembic.ini upgrade head
```
