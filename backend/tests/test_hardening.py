"""Durcissement : refus d'une connexion, limites par compte, liens annulés, fuites, config."""
import io
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from auth_kit.adapters import hibp
from auth_kit.adapters.hibp import HibpBreachChecker
from auth_kit.db import normalize_database_url
from auth_kit.models import EmailVerification, UserSession
from auth_kit.security import get_password_hash, verify_password
from auth_kit.services.maintenance import cleanup
from tests.conftest import (
    PASSWORD, _skip_login_cooldown, app, bearer, kit, limiter, link_token, login, make_user, settings,
)

NEW_PASSWORD = "nouveau-mot-de-passe-solide"


def _start_login(client, outbox, username="alice", password=PASSWORD) -> str:
    _skip_login_cooldown()
    r = client.post("/auth/token", data={"username": username, "password": password},
                    headers={"User-Agent": "Navigateur-De-Test/1.0"})
    assert r.status_code == 202, r.json()
    return r.json()["attempt_id"]


# --- Connexion par email ------------------------------------------------------------------

def test_mail_de_login_donne_le_contexte(client, outbox):
    make_user("alice")
    _start_login(client, outbox)
    text = outbox[-1].text
    assert "testclient" in text and "Navigateur-De-Test/1.0" in text and "UTC" in text
    assert "&type=login" in text


def test_ce_n_est_pas_moi(client, outbox):
    make_user("alice")
    attempt_id = _start_login(client, outbox)
    token = link_token(outbox)

    r = client.post("/auth/login/deny", json={"token": token})
    assert r.status_code == 200 and "changez-le" in r.json()["message"]
    # La page de l'attaquant ne reçoit jamais de tokens, et le lien ne peut plus approuver
    assert client.post("/auth/login/claim", json={"attempt_id": attempt_id}).json()["code"] == "login_link_expired"
    assert client.post("/auth/verify", json={"token": token}).json()["code"] == "invalid_link"
    assert client.post("/auth/login/deny", json={"token": token}).json()["code"] == "invalid_link"


def test_refus_n_accepte_que_les_liens_de_login(client, outbox):
    make_user("alice", verified=False)
    client.post("/auth/resend-verification", json={"email": "alice@example.com"})
    assert client.post("/auth/login/deny", json={"token": link_token(outbox)}).json()["code"] == "invalid_link"


# --- Limites ------------------------------------------------------------------------------

def test_limite_d_echecs_par_compte_toutes_ip(outbox):
    make_user("alice")
    limiter.enabled = True
    # 10 échecs depuis 10 IP différentes : la limite par IP ne se déclenche jamais
    for i in range(10):
        attacker = TestClient(app, client=(f"10.0.0.{i}", 50000))
        r = attacker.post("/auth/token", data={"username": "alice", "password": "mauvais-mot-de-passe"})
        assert r.json()["code"] == "invalid_credentials"

    # Compte bloqué pour la fenêtre, même avec le bon mot de passe et une nouvelle IP
    r = TestClient(app, client=("10.0.1.1", 50000)).post("/auth/token", data={"username": "alice", "password": PASSWORD})
    assert (r.status_code, r.json()["code"]) == (429, "rate_limited")
    # Les autres comptes ne sont pas touchés
    make_user("bob")
    r = TestClient(app, client=("10.0.1.2", 50000)).post("/auth/token", data={"username": "bob", "password": PASSWORD})
    assert r.status_code == 202


def test_temps_constant_pour_un_username_inconnu(client, monkeypatch):
    from auth_kit.services import accounts as crud_user

    calls = []
    monkeypatch.setattr(crud_user, "burn_password_check", lambda: calls.append(1))
    r = client.post("/auth/token", data={"username": "fantome", "password": PASSWORD})
    assert r.json()["code"] == "invalid_credentials" and calls == [1]


def test_avis_compte_existant_limite_par_adresse(client, outbox):
    make_user("alice")
    limiter.enabled = True
    body = {"username": "bob", "email": "alice@example.com", "password": PASSWORD}
    client.post("/auth/register", json=body)
    client.post("/auth/register", json={**body, "username": "bob2"})
    assert len(outbox) == 1


# --- Liens annulés par un changement de mot de passe --------------------------------------

def test_changement_de_mot_de_passe_annule_les_liens_en_attente(client, outbox, db):
    make_user("alice")
    tokens = login(client, outbox)

    client.post("/auth/password/forgot", json={"email": "alice@example.com"})
    reset_token = link_token(outbox)
    # Tentative de connexion d'un tiers qui connaît l'ancien mot de passe
    attacker = TestClient(app)
    attempt_id = _start_login(attacker, outbox)
    login_token = link_token(outbox)

    r = client.post("/auth/password/change", headers=bearer(tokens),
                    json={"current_password": PASSWORD, "new_password": NEW_PASSWORD})
    assert r.status_code == 200

    assert client.post("/auth/password/reset", json={"token": reset_token, "new_password": "encore-autre-mdp-1"}).json()["code"] == "invalid_link"
    assert client.post("/auth/verify", json={"token": login_token}).json()["code"] == "invalid_link"
    assert attacker.post("/auth/login/claim", json={"attempt_id": attempt_id}).json()["code"] == "login_link_expired"


# --- Mots de passe ------------------------------------------------------------------------

class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _hibp_answer(password: str, count: int = 42):
    import hashlib

    suffix = hashlib.sha1(password.encode()).hexdigest().upper()[5:]
    body = f"0000000000000000000000000000000000A:0\r\n{suffix}:{count}\r\n".encode()
    return lambda request, timeout: _FakeResponse(body)


def test_mot_de_passe_fuite_refuse(client, monkeypatch):
    monkeypatch.setattr(kit.ctx, "breach_checker", HibpBreachChecker())
    monkeypatch.setattr(hibp.urllib.request, "urlopen", _hibp_answer(PASSWORD))
    r = client.post("/auth/register", json={"username": "bob", "email": "bob@example.com", "password": PASSWORD})
    assert r.status_code == 422 and "fuites" in r.json()["fields"]["password"]


def test_hibp_ne_compte_pas_les_lignes_de_remplissage(monkeypatch):
    monkeypatch.setattr(hibp.urllib.request, "urlopen", _hibp_answer(PASSWORD, count=0))
    assert HibpBreachChecker().is_breached(PASSWORD) is False


def test_hibp_injoignable_n_empeche_pas_l_inscription(client, monkeypatch):
    def panne(request, timeout):
        raise OSError("réseau coupé")

    monkeypatch.setattr(kit.ctx, "breach_checker", HibpBreachChecker())
    monkeypatch.setattr(hibp.urllib.request, "urlopen", panne)
    r = client.post("/auth/register", json={"username": "bob", "email": "bob@example.com", "password": PASSWORD})
    assert r.status_code == 201


def test_bcrypt_au_dela_de_72_octets():
    hashed = get_password_hash(PASSWORD)
    assert verify_password(PASSWORD, hashed)
    assert verify_password("é" * 40, hashed) is False   # 80 octets : refusé sans exception
    assert verify_password(PASSWORD, "pas-un-hash-bcrypt") is False


# --- Admin --------------------------------------------------------------------------------

def test_recherche_admin_sans_jokers(client, outbox):
    make_user("root", role="admin")
    make_user("alice")
    tokens = login(client, outbox, "root")
    for search in ("%", "_", "a%"):
        r = client.get("/admin/users", params={"search": search}, headers=bearer(tokens))
        assert r.json()["total"] == 0, search


# --- Configuration et déploiement ---------------------------------------------------------

def test_page_de_test_verify_desactivee_par_defaut(client, monkeypatch):
    assert client.get("/auth/verify").status_code == 404
    monkeypatch.setattr(settings, "verify_test_page", True)
    assert client.get("/auth/verify").status_code == 200


@pytest.mark.parametrize(("url", "sslmode", "expected_url", "expected_args"), [
    ("postgresql://u:p@h/db", "require", "postgresql+psycopg://u:p@h/db", {"sslmode": "require"}),
    ("postgresql://u:p@h/db", "disable", "postgresql+psycopg://u:p@h/db", {"sslmode": "disable"}),
    ("postgresql://u:p@h/db", "", "postgresql+psycopg://u:p@h/db", {}),
    ("postgresql://u:p@h/db?sslmode=verify-full", "require", "postgresql+psycopg://u:p@h/db?sslmode=verify-full", {}),
    ("sqlite:///./auth.db", "require", "sqlite:///./auth.db", {}),
])
def test_sslmode_configurable(url, sslmode, expected_url, expected_args):
    assert normalize_database_url(url, sslmode) == (expected_url, expected_args)


def test_nettoyage(client, outbox, db):
    make_user("alice")
    login(client, outbox)
    now = datetime.now(timezone.utc)
    later = now + timedelta(days=30)

    assert cleanup(db, keep_days=7, now=now) == (0, 0)
    links, sessions = cleanup(db, keep_days=7, now=later)
    assert links >= 1 and sessions == 1
    assert db.query(EmailVerification).count() == 0 and db.query(UserSession).count() == 0
