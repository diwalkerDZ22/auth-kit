"""Fixtures communes.

Les tests montent le kit dans une application de test, comme le ferait un projet :
base SQLite temporaire, mails en mémoire (MemoryEmailSender), rate-limit coupé par défaut.
"""
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from auth_kit import AuthKit, AuthSettings
from auth_kit.adapters import LimitsRateLimiter, MemoryEmailSender
from auth_kit.db import create_engine_from_url, session_dependency
from auth_kit.models import Base, EmailVerification, Role, User
from auth_kit.security import get_password_hash

PASSWORD = "cheval-batterie-agrafe"
CSRF = {"X-CSRF-Protection": "1"}

_DB_PATH = os.path.join(tempfile.mkdtemp(prefix="auth-kit-tests-"), "test.db")
engine = create_engine_from_url(f"sqlite:///{_DB_PATH}")
SessionLocal = sessionmaker(bind=engine, autoflush=False)

settings = AuthSettings(
    secret_key="cle-de-test-uniquement-pour-pytest-0123456789",
    login_email_required=True,
    cookie_secure=False,   # le TestClient parle en HTTP : un cookie Secure ne serait pas renvoyé
)
email_sender = MemoryEmailSender()
limiter = LimitsRateLimiter("memory://", enabled=False)
kit = AuthKit(settings=settings, get_db=session_dependency(SessionLocal), email=email_sender, rate_limiter=limiter)

app = FastAPI()
kit.install(app)


@pytest.fixture(autouse=True)
def database():
    """Base vide + rôles du kit avant chaque test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    kit.seed_roles(db)
    db.close()
    yield


@pytest.fixture(autouse=True)
def no_rate_limit():
    """Rate-limit coupé par défaut ; un test peut le réactiver (limiter.enabled = True)."""
    limiter.reset()
    limiter.enabled = False
    yield
    limiter.enabled = False


@pytest.fixture(autouse=True)
def outbox():
    """Mails « envoyés » pendant le test."""
    email_sender.outbox.clear()
    email_sender.fail = False
    yield email_sender.outbox
    email_sender.fail = False


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def make_user(username="alice", email=None, password=PASSWORD, role="user", verified=True, disabled=False) -> int:
    db = SessionLocal()
    role_id = db.query(Role).filter(Role.name == role).one().id
    user = User(
        username=username,
        email=email or f"{username}@example.com",
        hashed_password=get_password_hash(password),
        role_id=role_id,
        is_verified=verified,
        disabled=disabled,
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()
    return user_id


def link_token(outbox) -> str:
    """Token du dernier lien envoyé par email."""
    match = re.search(r"token=([A-Za-z0-9_-]+)", outbox[-1].text)
    assert match, "aucun lien dans le dernier mail"
    return match.group(1)


def _skip_login_cooldown() -> None:
    """Vieillit les liens de login déjà créés : l'anti-spam (1 mail / min) ne bloque pas le test."""
    db = SessionLocal()
    db.query(EmailVerification).filter(EmailVerification.purpose == "login").update(
        {"created_at": datetime.now(timezone.utc) - timedelta(minutes=5)}, synchronize_session=False
    )
    db.commit()
    db.close()


def login(client, outbox, username="alice", password=PASSWORD) -> dict:
    """Connexion complète : mot de passe, clic sur le lien, récupération des tokens."""
    _skip_login_cooldown()
    r = client.post("/auth/token", data={"username": username, "password": password})
    assert r.status_code == 202, r.json()
    attempt_id = r.json()["attempt_id"]
    assert client.post("/auth/verify", json={"token": link_token(outbox)}).status_code == 200
    r = client.post("/auth/login/claim", json={"attempt_id": attempt_id})
    assert r.status_code == 200, r.json()
    return r.json()


def bearer(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}
