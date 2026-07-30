import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.base import Base

# Ce fichier est chargé automatiquement par pytest (convention "conftest.py")
# et définit des "fixtures" : des fonctions réutilisables qu'on peut demander
# en paramètre dans un test (ex: `def test_x(db_session): ...`) et que pytest
# se charge d'exécuter et de nettoyer pour nous.


@pytest.fixture(scope="session")
def engine():
    """Crée toutes les tables une seule fois pour l'ensemble des tests
    (scope="session"), plutôt qu'à chaque test, pour aller plus vite.
    Se connecte à une base PostgreSQL de test (voir DATABASE_URL en CI).
    """
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie_test",
    )
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine  # les tests s'exécutent ici
    Base.metadata.drop_all(engine)  # nettoyage une fois tous les tests terminés
    engine.dispose()


@pytest.fixture
def db_session(engine):
    """Fournit une session de base de données isolée pour UN SEUL test.

    Astuce classique : on ouvre une transaction avant le test et on
    l'annule (rollback) après, au lieu de faire un vrai commit. Comme ça,
    les données créées par un test (ex: un film "Dune") ne polluent pas
    les tests suivants, sans avoir à les supprimer une par une.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()

    yield session  # le test utilise `session` ici

    session.close()
    transaction.rollback()
    connection.close()
