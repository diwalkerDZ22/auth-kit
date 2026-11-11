"""Fixtures communes.

Les tests tournent sur une base SQLite temporaire (jamais sur la base du .env)
et interceptent l'envoi Resend : aucun vrai email ne part.
"""
import os
import re
import tempfile
from datetime import datetime, timedelta, timezone

# Avant tout import de app.* : ces variables d'environnement l'emportent sur le .env
_DB_PATH = os.path.join(tempfile.mkdtemp(prefix="auth-kit-tests-"), "test.db")
os.environ.update({
    "DATABASE_URL": f"sqlite:///{_DB_PATH}",
    "SECRET_KEY": "cle-de-test-uniquement-pour-pytest-0123456789",
    "RESEND_API_KEY": "re_test",
    "LOGIN_EMAIL_REQUIRED": "true",
    "COOKIE_SECURE": "false",   # le TestClient parle en HTTP : un cookie Secure ne serait pas renvoyé
    "LOG_LEVEL": "WARNING",
})

import pytest
import resend
from fastapi.testclient import TestClient

from app.core.limiter import limiter
from app.core.security import get_password_hash
from app.db.base import Base, SessionLocal, engine
from app.db.models import EmailVerification, Permission, Role, User
from app.main import app

PASSWORD = "cheval-batterie-agrafe"
CSRF = {"X-CSRF-Protection": "1"}


@pytest.fixture(autouse=True)
def database():
    """Base vide + rôles du kit avant chaque test."""
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    manage = Permission(code="users:manage", description="Gérer les utilisateurs")
    db.add_all([
        Role(name="user", description="Utilisateur standard", permissions=[]),
        Role(name="admin", description="Administrateur", permissions=[manage]),
    ])
    db.commit()
    db.close()
    yield


@pytest.fixture(autouse=True)
def no_rate_limit():
    """Rate-limit coupé par défaut ; un test peut le réactiver."""
    limiter.reset()
    limiter.enabled = False
    yield
    limiter.enabled = False


@pytest.fixture(autouse=True)
def outbox(monkeypatch):
    """Remplace l'envoi Resend : les mails sont stockés dans une liste."""
    sent: list[dict] = []
    monkeypatch.setattr(resend.Emails, "send", lambda params: sent.append(params) or {"id": "test"})
    return sent


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


def link_token(outbox: list[dict]) -> str:
    """Token du dernier lien envoyé par email."""
    match = re.search(r"token=([A-Za-z0-9_-]+)", outbox[-1]["text"])
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
