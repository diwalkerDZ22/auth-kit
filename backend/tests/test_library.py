"""Le kit comme bibliothèque : fonctionnalités optionnelles, extensions du projet, isolation."""
from dataclasses import replace

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from auth_kit import ApiError, AuthKit, EmailTemplates, LinkEmail, RoleSpec
from auth_kit.adapters import MemoryEmailSender, NoRateLimiter
from auth_kit.db import session_dependency
from auth_kit.models import Role, User
from tests.conftest import PASSWORD, SessionLocal, bearer, link_token, login, make_user, settings


def _kit(**kwargs) -> tuple[AuthKit, MemoryEmailSender]:
    sender = kwargs.pop("email", None) or MemoryEmailSender()
    kit = AuthKit(
        settings=kwargs.pop("settings", settings),
        get_db=session_dependency(SessionLocal),
        email=sender,
        rate_limiter=NoRateLimiter(),
        **kwargs,
    )
    return kit, sender


def _app(kit: AuthKit, **install) -> FastAPI:
    app = FastAPI()
    kit.install(app, **install)
    return app


def test_fonctionnalites_optionnelles():
    kit, _ = _kit(features=set())
    client = TestClient(_app(kit))
    assert client.post("/auth/register", json={}).status_code == 404
    assert client.post("/auth/password/forgot", json={}).status_code == 404
    assert client.get("/auth/sessions").status_code == 404
    assert client.get("/admin/users").status_code == 404
    # Le cœur reste là
    config = client.get("/auth/config").json()
    assert config["features"] == [] and config["login_email_required"] is True
    assert client.post("/auth/token", data={"username": "x", "password": "y"}).json()["code"] == "invalid_credentials"


def test_fonctionnalite_inconnue_refusee():
    with pytest.raises(ValueError, match="inconnues"):
        _kit(features={"register", "sso"})


def test_config_publique(client):
    config = client.get("/auth/config").json()
    assert config["features"] == ["admin", "devices", "password_reset", "register"]
    assert config["password"] == {"min_length": 8, "max_bytes": 72, "breach_check": False}
    assert config["username_pattern"].startswith("^")


def test_prefixes_configurables(outbox):
    kit, sender = _kit()
    client = TestClient(_app(kit, auth_prefix="/api/compte", admin_prefix="/api/gestion"))
    make_user("alice")
    r = client.post("/api/compte/token", data={"username": "alice", "password": PASSWORD})
    assert r.status_code == 202
    assert client.get("/auth/config").status_code == 404
    assert client.get("/api/gestion/users").json()["code"] == "not_authenticated"


def test_format_d_erreur_limite_aux_routes_du_kit():
    kit, _ = _kit()
    app = _app(kit)

    class Body(BaseModel):
        n: int

    @app.post("/metier")
    def metier(body: Body):
        return body

    client = TestClient(app)
    # Route du projet : format FastAPI par défaut, intact
    assert "detail" in client.post("/metier", json={"n": "x"}).json()
    assert "detail" in client.get("/inconnue").json()
    # Route du kit : format du kit
    r = client.post("/auth/register", json={})
    assert r.json()["code"] == "validation_error" and "username" in r.json()["fields"]


def test_format_d_erreur_sur_toute_l_application():
    kit, _ = _kit()
    app = _app(kit, error_scope="app")
    client = TestClient(app)
    assert client.get("/inconnue").json()["code"] == "not_found"


def test_codes_d_erreur_et_dependances_du_projet(outbox):
    kit, sender = _kit(errors={"job_not_found": (404, "Offre introuvable."), "invalid_credentials": (401, "Raté.")})
    app = _app(kit)

    @app.get("/jobs/{job_id}")
    def job(job_id: int, user: User = Depends(kit.current_user)):
        raise ApiError("job_not_found")

    @app.get("/stats", dependencies=[Depends(kit.require_permission("stats:read"))])
    def stats():
        return {"ok": True}

    client = TestClient(app)
    make_user("alice")
    tokens = login(client, sender.outbox)

    r = client.get("/jobs/1", headers=bearer(tokens))
    assert (r.status_code, r.json()) == (404, {"code": "job_not_found", "message": "Offre introuvable."})
    assert client.get("/stats", headers=bearer(tokens)).json()["code"] == "permission_denied"
    # Message du kit remplacé
    assert client.post("/auth/token", data={"username": "alice", "password": "faux"}).json()["message"] == "Raté."


def test_code_inconnu_rendu_en_500(caplog):
    kit, _ = _kit()
    app = _app(kit)

    @app.get("/auth/oups")
    def oups():
        raise ApiError("code_qui_n_existe_pas")

    r = TestClient(app).get("/auth/oups")
    assert (r.status_code, r.json()["code"]) == (500, "internal_error")
    assert "code_qui_n_existe_pas" in caplog.text


def test_roles_et_permissions_du_projet(db):
    kit, _ = _kit(
        permissions={"users:manage": "Admin", "jobs:classify": "Classer"},
        roles={
            "user": RoleSpec("Utilisateur"),
            "recruteur": RoleSpec("Recruteur", ("jobs:classify",)),
            "admin": RoleSpec("Admin", ("users:manage", "jobs:classify")),
        },
    )
    kit.seed_roles(db)
    kit.seed_roles(db)   # idempotent
    roles = {r.name: sorted(p.code for p in r.permissions) for r in db.query(Role).all()}
    assert roles == {"admin": ["jobs:classify", "users:manage"], "recruteur": ["jobs:classify"], "user": []}

    with pytest.raises(ValueError, match="non déclarées"):
        _kit(roles={"x": RoleSpec("X", ("inconnue",))})[0].seed_roles(db)


def test_mails_personnalisables(client):
    templates = replace(
        EmailTemplates(),
        brand_color="#0f766e",
        signup=LinkEmail("Confirm your email", "Welcome!", "One more step.", "Activate", "Ignore otherwise."),
    )
    kit, sender = _kit(templates=templates)
    client = TestClient(_app(kit))
    client.post("/auth/register", json={"username": "bob", "email": "bob@example.com", "password": PASSWORD})
    message = sender.outbox[-1]
    assert message.subject == "Confirm your email"
    assert "#0f766e" in message.html and "Activate" in message.html
    assert "token=" in message.text and link_token(sender.outbox)


def test_sub_est_l_id_utilisateur(client, outbox):
    user_id = make_user("alice")
    tokens = login(client, outbox)
    claims = jwt.decode(tokens["access_token"], options={"verify_signature": False})
    assert claims["sub"] == str(user_id) and claims["type"] == "access" and "sid" in claims


def test_rate_limit_pour_les_routes_du_projet():
    from auth_kit.adapters import LimitsRateLimiter

    kit = AuthKit(
        settings=settings,
        get_db=session_dependency(SessionLocal),
        email=MemoryEmailSender(),
        rate_limiter=LimitsRateLimiter("memory://"),
    )
    app = _app(kit)

    @app.get("/auth/ping", dependencies=[Depends(kit.rate_limit("2/minute"))])
    def ping():
        return {"ok": True}

    client = TestClient(app)
    assert [client.get("/auth/ping").status_code for _ in range(3)] == [200, 200, 429]


def test_deux_kits_independants():
    """Aucun état global : deux instances avec des réglages différents cohabitent."""
    kit_a, _ = _kit()
    kit_b, _ = _kit(settings=settings.model_copy(update={"login_email_required": False}))
    a, b = TestClient(_app(kit_a)), TestClient(_app(kit_b))
    assert a.get("/auth/config").json()["login_email_required"] is True
    assert b.get("/auth/config").json()["login_email_required"] is False
