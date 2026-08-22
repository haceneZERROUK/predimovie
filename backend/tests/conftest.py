import os

import pytest
from sqlalchemy import create_engine

from database.base import Base

# backend/auth.py ouvre ses propres sessions (via database.base.SessionLocal),
# pas les fixtures a rollback de database/tests/conftest.py. Il faut donc
# s'assurer nous-memes que les tables existent avant de lancer ces tests.


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
