"""Connexion en deux étapes : mot de passe, puis lien reçu par email (approuver ou refuser)."""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.errors import ApiError
from auth_kit.models import EmailVerification, User
from auth_kit.services.accounts import authenticate
from auth_kit.services.sessions import ClientInfo
from auth_kit.services.verification import (
    create_link, discard_pending_links, find_active_link, hash_token, sent_recently,
)
from auth_kit.templates import render_link_email

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoginStarted:
    attempt_id: str   # secret de la page de login, à présenter à claim()


def check_password(db: Session, ctx: KitContext, username: str, password: str) -> User:
    """Étape 1 : identifiants + état du compte. Limite d'échecs par compte, toutes IP confondues."""
    limit = ctx.settings.login_failures_per_account
    account_key = username.lower()
    # Vérifié avant bcrypt ; un compte attaqué reste bloqué jusqu'à la fin de la fenêtre,
    # même avec le bon mot de passe (sinon ce ne serait pas une limite).
    if not ctx.limiter.test(limit, "login-failures", account_key):
        logger.warning("Connexion bloquée : trop d'échecs pour le username %r", username)
        raise ApiError("rate_limited")

    user = authenticate(db, username, password)
    if not user:
        ctx.limiter.hit(limit, "login-failures", account_key)
        logger.info("Échec de connexion pour le username %r", username)
        raise ApiError("invalid_credentials", headers={"WWW-Authenticate": "Bearer"})
    if user.disabled:
        logger.info("Connexion refusée à %s : compte désactivé", user.username)
        raise ApiError("account_disabled")
    if not user.is_verified:
        logger.info("Connexion refusée à %s : email non vérifié", user.username)
        raise ApiError("email_not_verified")
    return user


def start_email_login(db: Session, ctx: KitContext, user: User, client: ClientInfo) -> LoginStarted:
    """Envoie le lien de connexion (synchrone : on ne dit « envoyé » que s'il est vraiment parti)."""
    s = ctx.settings
    if sent_recently(db, user, "login", s.login_email_cooldown_seconds):
        logger.info("Email de login redemandé trop tôt par %s", user.username)
        raise ApiError("login_email_cooldown")

    attempt_secret = secrets.token_urlsafe(32)
    link = create_link(db, ctx, user, "login", attempt_secret)
    # Le mail dit qui demande la connexion : l'utilisateur peut refuser une demande qui n'est pas la sienne
    context = {
        "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
        "ip": client.ip,
        "browser": client.user_agent,
    }
    message = render_link_email(ctx.templates, s.app_name, user.email, link, "login", context)
    if not ctx.email.send(message):
        discard_pending_links(db, user, "login")
        logger.warning("Email de login non envoyé pour %s", user.username)
        raise ApiError("email_unavailable")
    logger.info("Email de login envoyé pour %s", user.username)
    return LoginStarted(attempt_secret)


def claim(db: Session, ctx: KitContext, attempt_id: str) -> User | None:
    """Étape 2, interrogée en boucle par la page de login. None : lien pas encore cliqué."""
    now = datetime.now(timezone.utc)
    v = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.attempt_hash == hash_token(attempt_id),
            EmailVerification.purpose == "login",
            EmailVerification.claimed_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if not v:
        raise ApiError("login_attempt_unknown")

    if v.approved_at is None:
        if v.used_at is not None or v.expires_at <= now:
            raise ApiError("login_link_expired")   # remplacé, refusé ou expiré
        return None

    if now - v.approved_at > timedelta(minutes=ctx.settings.login_claim_window_minutes):
        raise ApiError("login_approval_expired")
    user = v.user
    if not user.is_verified or user.disabled:
        raise ApiError("account_not_allowed")

    v.claimed_at = now
    db.commit()
    logger.info("Tokens remis à la page de login de %s", user.username)
    return user


def confirm_link(db: Session, token: str) -> str:
    """Clic sur un lien signup (active le compte) ou login (approuve la connexion). Renvoie le purpose."""
    verification = find_active_link(db, token, ("signup", "login"))   # un lien de reset passe par reset()
    if not verification:
        logger.info("Lien de vérification invalide ou expiré")
        raise ApiError("invalid_link")

    now = datetime.now(timezone.utc)
    user = verification.user
    verification.used_at = now   # lien à usage unique

    if verification.purpose == "signup":
        user.is_verified = True
        db.commit()
        logger.info("Email vérifié pour %s", user.username)
        return "signup"

    if not user.is_verified or user.disabled:
        db.commit()   # le lien reste consommé
        raise ApiError("account_not_allowed")
    verification.approved_at = now   # aucun token émis ici : la page d'origine les récupère par claim()
    db.commit()
    logger.info("Connexion approuvée par email pour %s", user.username)
    return "login"


def deny(db: Session, token: str) -> None:
    """« Ce n'est pas moi » : annule la demande. La page d'origine reçoit login_link_expired."""
    verification = find_active_link(db, token, ("login",))
    if not verification:
        raise ApiError("invalid_link")
    verification.used_at = datetime.now(timezone.utc)
    db.commit()
    logger.warning("Demande de connexion refusée par le titulaire du compte %s", verification.user.username)
