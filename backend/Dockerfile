FROM python:3.11-slim

WORKDIR /app

# on copie tout le projet : le backend importe database/ et ml/
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY database ./database
COPY ml ./ml

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
