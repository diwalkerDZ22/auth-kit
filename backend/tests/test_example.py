"""Application de démo et contrat OpenAPI partagé avec le frontend."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from example.openapi import build_openapi, dump

CONTRACT = Path(__file__).resolve().parents[2] / "frontend" / "packages" / "auth-kit" / "openapi.json"


@pytest.fixture
def example_app(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'demo.db'}")
    monkeypatch.setenv("AUTH_SECRET_KEY", "cle-de-test-uniquement-0123456789-abcdef")
    monkeypatch.setenv("EMAIL_BACKEND", "console")
    monkeypatch.setenv("PASSWORD_BREACH_CHECK", "false")
    from example.main import create_app

    return create_app(env_file=None)


def test_application_de_demo_demarre(example_app):
    client = TestClient(example_app)
    assert client.get("/auth/config").status_code == 200
    assert client.get("/hello").json()["code"] == "not_authenticated"


def test_cors_autorise_le_header_csrf(example_app):
    r = TestClient(example_app).options("/auth/refresh", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-csrf-protection",
    })
    assert r.status_code == 200
    assert "x-csrf-protection" in r.headers["access-control-allow-headers"].lower()


def test_contrat_openapi_a_jour():
    """Le frontend génère ses types depuis ce fichier : il doit suivre le backend.

    En cas d'échec : cd backend && python -m example.openapi ../frontend/packages/auth-kit/openapi.json
    puis cd frontend && npm run gen:api
    """
    assert CONTRACT.exists(), f"{CONTRACT} absent"
    assert CONTRACT.read_text(encoding="utf-8") == dump(build_openapi()), "openapi.json n'est plus à jour"
