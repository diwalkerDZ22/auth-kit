"""Inscription, vérification, connexion par email, tokens, révocation."""
import resend

from app.core.limiter import limiter
from tests.conftest import PASSWORD, bearer, link_token, login, make_user


def test_inscription_verification_et_connexion(client, outbox):
    r = client.post("/auth/register", json={"username": "alice", "email": "Alice@Example.com", "password": PASSWORD})
    assert r.status_code == 201
    assert r.json()["email"] == "alice@example.com" and r.json()["is_verified"] is False

    # Connexion refusée tant que l'email n'est pas vérifié
    r = client.post("/auth/token", data={"username": "alice", "password": PASSWORD})
    assert r.json()["code"] == "email_not_verified"

    assert client.post("/auth/verify", json={"token": link_token(outbox)}).json()["purpose"] == "signup"

    # Avant le clic sur le lien de connexion : en attente
    r = client.post("/auth/token", data={"username": "alice", "password": PASSWORD})
    attempt_id = r.json()["attempt_id"]
    assert client.post("/auth/login/claim", json={"attempt_id": attempt_id}).json()["code"] == "login_pending"

    client.post("/auth/verify", json={"token": link_token(outbox)})
    tokens = client.post("/auth/login/claim", json={"attempt_id": attempt_id}).json()
    me = client.get("/auth/me", headers=bearer(tokens)).json()
    assert me["username"] == "alice" and me["role"] == "user" and me["permissions"] == []

    # Une tentative ne se récupère qu'une fois
    assert client.post("/auth/login/claim", json={"attempt_id": attempt_id}).json()["code"] == "login_attempt_unknown"


def test_regles_inscription(client):
    cas = [
        ({"username": "a b", "email": "x@example.com", "password": PASSWORD}, "username"),
        ({"username": "bob", "email": "x@example.com", "password": "court"}, "password"),
        ({"username": "bob", "email": "x@example.com", "password": "password123"}, "password"),
        ({"username": "bobby123", "email": "x@example.com", "password": "BOBBY123"}, "password"),
        ({"username": "bob", "email": "pas-un-email", "password": PASSWORD}, "email"),
    ]
    for body, champ in cas:
        r = client.post("/auth/register", json=body)
        assert r.status_code == 422, body
        assert champ in r.json()["fields"], (body, r.json())


def test_conflits_inscription(client):
    make_user("alice")
    r = client.post("/auth/register", json={"username": "alice", "email": "autre@example.com", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (409, "username_taken")
    r = client.post("/auth/register", json={"username": "bob", "email": "ALICE@example.com", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (409, "email_taken")


def test_refresh_et_type_de_token(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)

    # Un refresh token ne sert pas d'access token
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"})
    assert r.json()["code"] == "invalid_token"

    new = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    assert client.get("/auth/me", headers=bearer(new)).status_code == 200
    # L'ancien refresh token est remplacé
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.json()["code"] == "invalid_refresh_token"


def test_logout_revoque_immediatement(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)
    assert client.post("/auth/logout", headers=bearer(tokens)).status_code == 200
    assert client.get("/auth/me", headers=bearer(tokens)).json()["code"] == "invalid_token"
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.json()["code"] == "invalid_refresh_token"


def test_resend_en_panne_au_login(client, outbox, monkeypatch):
    make_user("alice")

    def panne(params):
        raise RuntimeError("Resend indisponible")

    monkeypatch.setattr(resend.Emails, "send", panne)
    r = client.post("/auth/token", data={"username": "alice", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (503, "email_unavailable")
    assert "attempt_id" not in r.json()

    # Le mail raté ne compte pas pour l'anti-spam : on peut réessayer tout de suite
    monkeypatch.setattr(resend.Emails, "send", lambda params: outbox.append(params) or {"id": "test"})
    assert client.post("/auth/token", data={"username": "alice", "password": PASSWORD}).status_code == 202


def test_lien_de_reset_refuse_sur_verify(client, outbox):
    make_user("alice")
    client.post("/auth/password/forgot", json={"email": "alice@example.com"})
    r = client.post("/auth/verify", json={"token": link_token(outbox)})
    assert (r.status_code, r.json()["code"]) == (400, "invalid_link")


def test_rate_limit(client):
    limiter.enabled = True
    codes = [client.post("/auth/verify", json={"token": "faux"}).status_code for _ in range(11)]
    assert codes[:10] == [400] * 10
    assert codes[10] == 429
