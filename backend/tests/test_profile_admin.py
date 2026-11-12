"""Profil et administration."""
from auth_kit.services.admin import count_active_admins
from tests.conftest import PASSWORD, bearer, login, make_user


def test_modifier_son_profil(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)
    r = client.patch("/auth/me", headers=bearer(tokens), json={"full_name": "  Alice Martin  "})
    assert r.status_code == 200 and r.json()["full_name"] == "Alice Martin"
    r = client.patch("/auth/me", headers=bearer(tokens), json={"full_name": "x" * 101})
    assert r.status_code == 422 and "full_name" in r.json()["fields"]


def test_admin_reserve_aux_admins(client, outbox):
    make_user("alice")
    tokens = login(client, outbox)
    assert client.get("/admin/users", headers=bearer(tokens)).json()["code"] == "permission_denied"


def test_admin_liste_recherche_et_detail(client, outbox):
    make_user("root", role="admin")
    for name in ("alice", "bob", "carole"):
        make_user(name)
    tokens = login(client, outbox, "root")

    page = client.get("/admin/users?limit=2&offset=0", headers=bearer(tokens)).json()
    assert page["total"] == 4 and len(page["items"]) == 2
    found = client.get("/admin/users?search=CAR", headers=bearer(tokens)).json()
    assert [u["username"] for u in found["items"]] == ["carole"]
    r = client.get("/admin/users?limit=500", headers=bearer(tokens))
    assert r.status_code == 422 and "limit" in r.json()["fields"]

    assert client.get("/admin/users/999", headers=bearer(tokens)).json()["code"] == "user_not_found"
    roles = client.get("/admin/roles", headers=bearer(tokens)).json()
    assert {r["name"]: r["permissions"] for r in roles} == {"admin": ["users:manage"], "user": []}


def test_admin_desactive_un_compte(client, outbox):
    make_user("root", role="admin")
    bob_id = make_user("bob")
    admin = login(client, outbox, "root")
    bob = login(client, outbox, "bob")

    r = client.patch(f"/admin/users/{bob_id}", headers=bearer(admin), json={"disabled": True})
    assert r.status_code == 200 and r.json()["disabled"] is True

    # Effet immédiat : la session de bob est coupée et il ne peut plus se connecter
    assert client.get("/auth/me", headers=bearer(bob)).json()["code"] == "invalid_token"
    r = client.post("/auth/token", data={"username": "bob", "password": PASSWORD})
    assert r.json()["code"] == "account_disabled"


def test_admin_change_un_role(client, outbox):
    make_user("root", role="admin")
    bob_id = make_user("bob")
    admin = login(client, outbox, "root")

    assert client.patch(f"/admin/users/{bob_id}", headers=bearer(admin), json={"role": "inconnu"}).json()["code"] == "role_not_found"
    r = client.patch(f"/admin/users/{bob_id}", headers=bearer(admin), json={"role": "admin"})
    assert r.json()["role"] == "admin"

    bob = login(client, outbox, "bob")
    assert client.get("/admin/users", headers=bearer(bob)).status_code == 200


def test_admin_ne_se_modifie_pas_lui_meme(client, outbox):
    root_id = make_user("root", role="admin")
    admin = login(client, outbox, "root")
    r = client.patch(f"/admin/users/{root_id}", headers=bearer(admin), json={"disabled": True})
    assert r.json()["code"] == "cannot_modify_self"


def test_compte_des_admins_actifs(db):
    root_id = make_user("root", role="admin")
    make_user("ancien", role="admin", disabled=True)
    make_user("alice")
    assert count_active_admins(db) == 1
    assert count_active_admins(db, exclude_user_id=root_id) == 0
