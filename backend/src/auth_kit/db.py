"""Aides pour la base de données. Le kit n'ouvre aucune connexion lui-même :
l'application fournit sa dépendance get_db à AuthKit.
"""
from collections.abc import Callable, Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def normalize_database_url(url: str, sslmode: str | None = "require") -> tuple[str, dict]:
    """Driver psycopg 3 pour PostgreSQL, et sslmode imposé sauf s'il est déjà dans l'URL.

    sslmode : "require" (défaut), "disable" pour un Postgres local sans SSL, None / "" pour ne rien imposer.
    """
    connect_args: dict = {}
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+") and sslmode and "sslmode=" not in url:
        connect_args["sslmode"] = sslmode
    return url, connect_args


def create_engine_from_url(url: str, sslmode: str | None = "require", **kwargs) -> Engine:
    url, connect_args = normalize_database_url(url, sslmode)
    return create_engine(url, connect_args={**connect_args, **kwargs.pop("connect_args", {})}, **kwargs)


def session_dependency(session_factory: sessionmaker) -> Callable[[], Iterator[Session]]:
    """Dépendance FastAPI qui ouvre une session par requête et la ferme ensuite."""
    def get_db() -> Iterator[Session]:
        db = session_factory()
        try:
            yield db
        finally:
            db.close()
    return get_db
