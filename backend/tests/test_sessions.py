"""Sessions par appareil : plusieurs appareils, rotation, délai de grâce, réutilisation, révocation."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from auth_kit.models import UserSession
from auth_kit.services.verification import hash_token
from tests.conftest import CSRF, PASSWORD, app, bearer, login, make_user


def _two_devices(outbox):
    laptop, phone = TestClient(app), TestClient(app)
    return laptop, login(laptop, outbox), phone, login(phone, outbox)


def test_plusieurs_appareils_restent_connectes(client, outbox):
    make_user("alice")
    laptop, laptop_tokens, phone, phone_tokens = _two_devices(outbox)

    # Se connecter sur le téléphone ne déconnecte plus l'ordinateur
    assert laptop.post("/auth/refresh", headers=CSRF).status_code == 200
    assert phone.post("/auth/refresh", headers=CSRF).status_code == 200
    assert laptop.get("/auth/me", headers=bearer(laptop_tokens)).status_code == 200


def test_logout_ne_ferme_que_cet_appareil(outbox):
    make_user("alice")
    laptop, laptop_tokens, phone, phone_tokens = _two_devices(outbox)

    assert laptop.post("/auth/logout", headers=CSRF).status_code == 200
    assert laptop.get("/auth/me", headers=bearer(laptop_tokens)).json()["code"] == "invalid_token"
    assert phone.get("/auth/me", headers=bearer(phone_tokens)).status_code == 200
    assert phone.post("/auth/refresh", headers=CSRF).status_code == 200


def test_refresh_token_stocke_hashe(client, outbox, db):
    make_user("alice")
    login(client, outbox)
    raw = client.cookies.get("refresh_token")
    session = db.query(UserSession).one()
    assert session.token_hash == hash_token(raw) and raw not in session.token_hash
    assert session.ip == "testclient"


def test_delai_de_grace_entre_onglets(client, outbox):
    make_user("alice")
    login(client, outbox)
    old_cookie = client.cookies.get("refresh_token")
    assert client.post("/auth/refresh", headers=CSRF).status_code == 200
    new_cookie = client.cookies.get("refresh_token")

    # Un autre onglet envoie encore l'ancien cookie juste après la rotation : accepté,
    # sans nouveau cookie (le navigateur a déjà le bon)
    other_tab = TestClient(app, cookies={"refresh_token": old_cookie})
    r = other_tab.post("/auth/refresh", headers=CSRF)
    assert r.status_code == 200 and "set-cookie" not in r.headers
    assert other_tab.get("/auth/me", headers=bearer(r.json())).status_code == 200

    # Le cookie courant continue de fonctionner
    assert TestClient(app, cookies={"refresh_token": new_cookie}).post("/auth/refresh", headers=CSRF).status_code == 200


def test_reutilisation_apres_le_delai_revoque_la_session(client, outbox, db):
    make_user("alice")
    tokens = login(client, outbox)
    stolen = client.cookies.get("refresh_token")
    assert client.post("/auth/refresh", headers=CSRF).status_code == 200

    # Le délai de grâce est passé : l'ancien token ne devrait plus jamais revenir
    db.query(UserSession).update({"rotated_at": datetime.now(timezone.utc) - timedelta(minutes=5)})
    db.commit()

    r = TestClient(app, cookies={"refresh_token": stolen}).post("/auth/refresh", headers=CSRF)
    assert r.json()["code"] == "invalid_refresh_token"
    # Par précaution, toute la session tombe : le token légitime aussi
    assert client.post("/auth/refresh", headers=CSRF).json()["code"] == "invalid_refresh_token"
    assert client.get("/auth/me", headers=bearer(tokens)).json()["code"] == "invalid_token"


def test_session_expiree(client, outbox, db):
    make_user("alice")
    login(client, outbox)
    db.query(UserSession).update({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)})
    db.commit()
    assert client.post("/auth/refresh", headers=CSRF).json()["code"] == "invalid_refresh_token"


def test_liste_et_fermeture_des_appareils(outbox):
    make_user("alice")
    laptop, laptop_tokens, phone, phone_tokens = _two_devices(outbox)

    sessions = laptop.get("/auth/sessions", headers=bearer(laptop_tokens)).json()
    assert len(sessions) == 2
    assert sorted(s["current"] for s in sessions) == [False, True]
    phone_id = next(s["id"] for s in sessions if not s["current"])

    r = laptop.delete(f"/auth/sessions/{phone_id}", headers=bearer(laptop_tokens))
    assert r.status_code == 200 and r.json()["current"] is False
    assert phone.get("/auth/me", headers=bearer(phone_tokens)).json()["code"] == "invalid_token"
    assert laptop.delete(f"/auth/sessions/{phone_id}", headers=bearer(laptop_tokens)).json()["code"] == "session_not_found"
    assert len(laptop.get("/auth/sessions", headers=bearer(laptop_tokens)).json()) == 1


def test_deconnecter_les_autres_appareils(outbox):
    make_user("alice")
    laptop, laptop_tokens, phone, phone_tokens = _two_devices(outbox)

    r = laptop.delete("/auth/sessions", headers=bearer(laptop_tokens))
    assert r.json()["count"] == 1
    assert phone.post("/auth/refresh", headers=CSRF).json()["code"] == "invalid_refresh_token"
    assert laptop.get("/auth/me", headers=bearer(laptop_tokens)).status_code == 200


def test_session_d_un_autre_compte_introuvable(outbox):
    make_user("alice")
    make_user("bob")
    alice_client, bob_client = TestClient(app), TestClient(app)
    alice = login(alice_client, outbox, "alice")
    bob = login(bob_client, outbox, "bob")
    bob_session = bob_client.get("/auth/sessions", headers=bearer(bob)).json()[0]["id"]

    r = alice_client.delete(f"/auth/sessions/{bob_session}", headers=bearer(alice))
    assert (r.status_code, r.json()["code"]) == (404, "session_not_found")
    assert bob_client.get("/auth/me", headers=bearer(bob)).status_code == 200


def test_changement_de_mot_de_passe_ferme_les_autres_appareils(outbox):
    make_user("alice")
    laptop, laptop_tokens, phone, phone_tokens = _two_devices(outbox)

    r = laptop.post("/auth/password/change", headers=bearer(laptop_tokens),
                    json={"current_password": PASSWORD, "new_password": "nouveau-mot-de-passe-solide"})
    assert r.status_code == 200
    assert phone.post("/auth/refresh", headers=CSRF).json()["code"] == "invalid_refresh_token"
    assert laptop.post("/auth/refresh", headers=CSRF).status_code == 200
