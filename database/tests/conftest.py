import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base

# Fixtures partagees par les tests de database/, chargees automatiquement
# par pytest


@pytest.fixture(scope="session")
def engine():
    """Cree les tables une fois pour toute la session de tests, sur la
    base postgres de test."""
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie_test",
    )
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Une session par test. On ouvre une transaction et on la rollback
    a la fin, comme ca chaque test repart d'une base propre."""
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
