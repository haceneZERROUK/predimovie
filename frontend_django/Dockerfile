FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# migrate cree la petite base sqlite locale de Django (sessions, admin),
# rien a voir avec la vraie base Postgres qui reste geree par le backend
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
