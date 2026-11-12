"""Environnement Alembic des tables du kit (branche "auth_kit").

URL de la base, par ordre de priorité :
    alembic -x database_url=postgresql://... upgrade head
    variable d'environnement DATABASE_URL (ou fichier .env du dossier courant)
sslmode PostgreSQL : DATABASE_SSLMODE (défaut "require", "disable" pour un Postgres local).

Projet qui a ses propres migrations : voir docs/Bibliotheque.md (version_locations).
"""
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

from auth_kit.db import create_engine_from_url
from auth_kit.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(".env")


def _database_url() -> str:
    url = context.get_x_argument(as_dictionary=True).get("database_url")
    if not url:
        _load_dotenv()
        url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("URL de base manquante : -x database_url=... ou variable DATABASE_URL")
    return url


def run_migrations_offline() -> None:
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine_from_url(
        _database_url(),
        sslmode=os.environ.get("DATABASE_SSLMODE", "require"),
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
