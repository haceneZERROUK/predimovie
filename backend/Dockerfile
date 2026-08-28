FROM python:3.11-slim

WORKDIR /app

# on copie tout le projet : le backend importe database/ et ml/
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY database ./database
COPY ml ./ml

RUN pip install --no-cache-dir .

EXPOSE 8000

# $PORT (assigne dynamiquement par Railway, healthcheck cible ce port-la)
# avec 8000 par defaut pour docker-compose en local, ou PORT n'est pas defini
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
