FROM python:3.11-slim

WORKDIR /app

# le POC veille est autonome, pas besoin des autres packages du projet
COPY pyproject.toml README.md ./
COPY veille ./veille

RUN pip install --no-cache-dir .

EXPOSE 8501

CMD ["streamlit", "run", "veille/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
