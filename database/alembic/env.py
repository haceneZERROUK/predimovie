# Alembic est l'outil de "migrations" : il compare le schéma défini par
# nos modèles Python (database/models/) à l'état réel de la base de
# données, puis génère (et applique) les instructions SQL nécessaires
# pour les faire correspondre (CREATE TABLE, ALTER TABLE, ...).
# Ce fichier est le point d'entrée qu'Alembic exécute à chaque commande
# `alembic revision` / `alembic upgrade` (voir database/alembic.ini).
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from database.base import Base
from database.models import *  # noqa: F401,F403 registers all models on Base.metadata

config = context.config
# On force l'URL de connexion depuis la variable d'environnement DATABASE_URL
# plutôt que de la coder en dur dans alembic.ini (pratique pour changer
# d'environnement : local, CI, production...).
config.set_main_option(
    "sqlalchemy.url",
    os.environ.get(
        "DATABASE_URL", "postgresql+psycopg2://predimovie:predimovie@localhost:5432/predimovie"
    ),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Base.metadata contient la description de toutes les tables (grâce à
# l'import `from database.models import *` ci-dessus) : c'est ce
# qu'Alembic compare à la base réelle pour détecter les différences.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Génère le SQL des migrations sans se connecter à la base (on écrit
    juste les requêtes dans un fichier, à exécuter plus tard soi-même)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode normal : se connecte réellement à la base et applique les
    migrations directement (c'est ce mode qui est utilisé en pratique)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
