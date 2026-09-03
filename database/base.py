import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    """Classe de base des modeles. Tout ce qui en herite est enregistre
    dans Base.metadata, ce qui sert a Alembic et aux tests."""

    pass


def get_engine(database_url: str | None = None):
    """Cree un engine vers la base, a partir de l'URL passee ou de
    DATABASE_URL."""
    return create_engine(database_url or os.environ["DATABASE_URL"])


# engine par defaut de l'app. La valeur en dur sert juste en local quand
# DATABASE_URL n'est pas definie.
engine = create_engine(
    os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie"
    )
)

# SessionLocal() ouvre une session pour lire/ecrire, puis commit ou
# rollback
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
