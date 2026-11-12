"""Liens envoyés par email (signup, login, reset) : création, recherche, anti-spam.

Seuls les SHA-256 du token du lien et de l'attempt_id sont stockés.
"""
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.models import EmailVerification, User

logger = logging.getLogger(__name__)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _ttl(ctx: KitContext, purpose: str) -> timedelta:
    s = ctx.settings
    if purpose == "signup":
        return timedelta(hours=s.signup_token_expire_hours)
    if purpose == "reset":
        return timedelta(minutes=s.reset_token_expire_minutes)
    return timedelta(minutes=s.login_token_expire_minutes)


def _base_url(ctx: KitContext, purpose: str) -> str:
    # Le lien de reset ouvre la page « nouveau mot de passe », pas la page de vérification
    return ctx.settings.frontend_reset_url if purpose == "reset" else ctx.settings.frontend_verify_url


def sent_recently(db: Session, user: User, purpose: str, seconds: int) -> bool:
    """Anti-spam : un lien de ce type a-t-il été créé il y a moins de `seconds` ?"""
    last = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == purpose)
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    return last is not None and datetime.now(timezone.utc) - last.created_at < timedelta(seconds=seconds)


def create_link(db: Session, ctx: KitContext, user: User, purpose: str, attempt_secret: str | None = None) -> str:
    """Crée un lien (et annule les anciens liens non utilisés du même type). Renvoie l'URL complète."""
    now = datetime.now(timezone.utc)
    (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user.id,
            EmailVerification.purpose == purpose,
            EmailVerification.used_at.is_(None),
        )
        .update({"used_at": now}, synchronize_session=False)
    )

    raw = secrets.token_urlsafe(32)   # part par email
    expires_at = now + _ttl(ctx, purpose)
    db.add(EmailVerification(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(raw),
        # secret de la page de login : seul son hash est stocké (None pour signup et reset)
        attempt_hash=hash_token(attempt_secret) if attempt_secret else None,
        expires_at=expires_at,
    ))
    db.commit()
    logger.info("Lien créé pour %s (purpose=%s, expire à %s)", user.username, purpose, expires_at)
    # "type" (pas secret) : la page du frontend adapte ses boutons (approuver / refuser une connexion)
    return f"{_base_url(ctx, purpose)}?token={raw}&type={purpose}"


def discard_pending_links(db: Session, user: User, purpose: str) -> None:
    """Supprime les liens encore actifs (ex. mail de login qui n'a pas pu partir).

    Supprimés plutôt que consommés : sinon l'anti-spam compterait un mail jamais envoyé.
    """
    (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user.id,
            EmailVerification.purpose == purpose,
            EmailVerification.used_at.is_(None),
        )
        .delete(synchronize_session=False)
    )
    db.commit()


def find_active_link(db: Session, token: str, purposes: tuple[str, ...]) -> EmailVerification | None:
    """Lien non utilisé et non expiré, verrouillé jusqu'au commit."""
    now = datetime.now(timezone.utc)
    return (
        db.query(EmailVerification)
        .filter(
            EmailVerification.token_hash == hash_token(token),
            EmailVerification.purpose.in_(purposes),
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
        )
        .with_for_update()
        .first()
    )
