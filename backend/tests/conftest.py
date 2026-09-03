import os

import pytest
from sqlalchemy import create_engine

from database.base import Base

# le backend ouvre ses propres sessions et pas les fixtures a rollback de
# database/tests, donc on cree les tables nous-memes avant les tests


@pytest.fixture(scope="session", autouse=True)
def creer_les_tables():
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie_test",
    )
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield
    engine.dispose()
