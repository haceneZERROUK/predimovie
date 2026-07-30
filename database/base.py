import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Classe de base dont hérite chaque modèle (Oeuvre, Acteur, ...).

    SQLAlchemy utilise cette classe pour savoir quelles classes Python
    correspondent à des tables SQL. Chaque modèle qui hérite de `Base`
    est automatiquement enregistré dans `Base.metadata`, ce qui permet
    ensuite de créer toutes les tables d'un coup (`Base.metadata.create_all`).
    """

    pass


def get_engine(database_url: str | None = None):
    """Crée une connexion (engine) vers la base, à partir d'une URL donnée
    ou, à défaut, de la variable d'environnement DATABASE_URL."""
    return create_engine(database_url or os.environ["DATABASE_URL"])


# Connexion par défaut utilisée par l'application (ex: FastAPI).
# La valeur de secours (après la virgule) ne sert que si DATABASE_URL
# n'est pas définie, par exemple en développement local sans .env chargé.
engine = create_engine(
    os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie"
    )
)

# SessionLocal() crée une "session" : une conversation avec la base de
# données dans laquelle on peut lire/écrire des objets, puis valider
# (commit) ou annuler (rollback) les changements.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
