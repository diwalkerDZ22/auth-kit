"""Inscription, vérification, connexion par email, tokens, révocation."""
from tests.conftest import CSRF, PASSWORD, bearer, email_sender, limiter, link_token, login, make_user


def test_inscription_verification_et_connexion(client, outbox):
    r = client.post("/auth/register", json={"username": "alice", "email": "Alice@Example.com", "password": PASSWORD})
    assert r.status_code == 201 and "message" in r.json()
    assert outbox[-1].to == "alice@example.com"   # email normalisé

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


def test_conflits_inscription(client, outbox, db):
    from auth_kit.models import User

    make_user("alice")
    r = client.post("/auth/register", json={"username": "alice", "email": "autre@example.com", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (409, "username_taken")

    # Email déjà inscrit : même réponse qu'une inscription réussie, aucun compte créé,
    # et le titulaire de l'adresse est prévenu (sans lien d'activation)
    libre = client.post("/auth/register", json={"username": "carole", "email": "carole@example.com", "password": PASSWORD})
    pris = client.post("/auth/register", json={"username": "bob", "email": "ALICE@example.com", "password": PASSWORD})
    assert (pris.status_code, pris.json()) == (libre.status_code, libre.json())
    assert db.query(User).filter(User.username == "bob").first() is None
    assert outbox[-1].to == "alice@example.com" and outbox[-1].purpose == "account_exists"
    assert "token=" not in outbox[-1].text


def test_refresh_token_uniquement_en_cookie(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)
    assert set(tokens) == {"access_token", "token_type", "expires_in"}
    refresh_token = client.cookies.get("refresh_token")
    assert refresh_token

    # Un refresh token ne sert pas d'access token
    r = client.get("/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
    assert r.json()["code"] == "invalid_token"


def test_refresh_par_cookie(client, outbox):
    make_user("alice")
    login(client, outbox)
    old_cookie = client.cookies.get("refresh_token")

    # Sans le header CSRF : refusé
    r = client.post("/auth/refresh")
    assert (r.status_code, r.json()["code"]) == (403, "csrf_missing")

    r = client.post("/auth/refresh", headers=CSRF)
    assert r.status_code == 200
    assert client.get("/auth/me", headers=bearer(r.json())).status_code == 200
    assert client.cookies.get("refresh_token") != old_cookie

    # L'ancien cookie est remplacé : refusé (une fois le délai de grâce passé), et effacé par la réponse
    from datetime import datetime, timedelta, timezone
    from auth_kit.models import UserSession
    from tests.conftest import SessionLocal

    db = SessionLocal()
    db.query(UserSession).update({"rotated_at": datetime.now(timezone.utc) - timedelta(minutes=5)})
    db.commit()
    db.close()
    client.cookies.clear()
    client.cookies.set("refresh_token", old_cookie)
    r = client.post("/auth/refresh", headers=CSRF)
    assert r.json()["code"] == "invalid_refresh_token"
    assert "refresh_token=" in r.headers["set-cookie"] and "Max-Age=0" in r.headers["set-cookie"]


def test_refresh_sans_cookie(client):
    r = client.post("/auth/refresh", headers=CSRF)
    assert (r.status_code, r.json()["code"]) == (401, "invalid_refresh_token")


def test_logout_revoque_immediatement(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)
    assert client.post("/auth/logout").json()["code"] == "csrf_missing"

    # Pas besoin d'access token : le cookie suffit (marche même s'il a expiré)
    assert client.post("/auth/logout", headers=CSRF).status_code == 200
    assert client.cookies.get("refresh_token") is None
    assert client.get("/auth/me", headers=bearer(tokens)).json()["code"] == "invalid_token"
    assert client.post("/auth/refresh", headers=CSRF).json()["code"] == "invalid_refresh_token"


def test_resend_en_panne_au_login(client, outbox):
    make_user("alice")
    email_sender.fail = True
    r = client.post("/auth/token", data={"username": "alice", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (503, "email_unavailable")
    assert "attempt_id" not in r.json()

    # Le mail raté ne compte pas pour l'anti-spam : on peut réessayer tout de suite
    email_sender.fail = False
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
