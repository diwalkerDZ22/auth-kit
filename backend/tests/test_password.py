"""Mot de passe oublié et changement de mot de passe."""
from tests.conftest import PASSWORD, bearer, link_token, login, make_user

NEW_PASSWORD = "nouveau-mot-de-passe-solide"


def test_forgot_email_inconnu(client, outbox):
    r = client.post("/auth/password/forgot", json={"email": "inconnu@example.com"})
    assert r.status_code == 200
    assert outbox == []


def test_reset_de_bout_en_bout(client, outbox):
    make_user("alice")
    old_tokens = login(client, outbox)

    message = client.post("/auth/password/forgot", json={"email": "ALICE@example.com"}).json()["message"]
    assert "Si un compte existe" in message
    assert "/reset-password?token=" in outbox[-1].text
    token = link_token(outbox)

    # Mot de passe refusé : le lien reste utilisable
    r = client.post("/auth/password/reset", json={"token": token, "new_password": "password"})
    assert r.status_code == 422 and "new_password" in r.json()["fields"]

    r = client.post("/auth/password/reset", json={"token": token, "new_password": NEW_PASSWORD})
    assert r.status_code == 200

    # Anciennes sessions coupées, ancien mot de passe refusé, nouveau accepté
    assert client.get("/auth/me", headers=bearer(old_tokens)).json()["code"] == "invalid_token"
    r = client.post("/auth/token", data={"username": "alice", "password": PASSWORD})
    assert r.json()["code"] == "invalid_credentials"
    login(client, outbox, password=NEW_PASSWORD)

    # Lien à usage unique
    r = client.post("/auth/password/reset", json={"token": token, "new_password": "encore-un-autre-mdp"})
    assert r.json()["code"] == "invalid_link"


def test_reset_verifie_le_compte(client, outbox, db):
    from auth_kit.models import User

    make_user("alice", verified=False)
    client.post("/auth/password/forgot", json={"email": "alice@example.com"})
    client.post("/auth/password/reset", json={"token": link_token(outbox), "new_password": NEW_PASSWORD})
    assert db.query(User).filter(User.username == "alice").one().is_verified is True


def test_changement_de_mot_de_passe(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)

    r = client.post("/auth/password/change", headers=bearer(tokens),
                    json={"current_password": "faux-mot-de-passe", "new_password": NEW_PASSWORD})
    assert (r.status_code, r.json()["code"]) == (400, "invalid_current_password")

    r = client.post("/auth/password/change", headers=bearer(tokens),
                    json={"current_password": PASSWORD, "new_password": PASSWORD})
    assert r.status_code == 422 and "new_password" in r.json()["fields"]

    r = client.post("/auth/password/change", headers=bearer(tokens),
                    json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert r.status_code == 200
    new_tokens = r.json()

    # La session courante continue avec les nouveaux tokens, les anciens sont révoqués
    assert client.get("/auth/me", headers=bearer(new_tokens)).status_code == 200
    assert client.get("/auth/me", headers=bearer(tokens)).json()["code"] == "invalid_token"
