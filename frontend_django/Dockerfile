FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# regroupe les statiques (logos, image de fond) dans staticfiles/, servi
# ensuite par WhiteNoise - fait au build, pas besoin de DB pour ca
RUN python manage.py collectstatic --noinput

EXPOSE 8000

# migrate cree la petite base sqlite locale de Django (sessions, admin),
# rien a voir avec la vraie base Postgres qui reste geree par le backend
#
# $PORT (assigne dynamiquement par Railway) avec 8000 par defaut en local -
# meme raison que backend/Dockerfile
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:${PORT:-8000}"]
