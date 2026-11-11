# app/core/verification.py
import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models import EmailVerification

logger = logging.getLogger(__name__)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _ttl(purpose: str) -> timedelta:
    if purpose == "signup":
        return timedelta(hours=settings.SIGNUP_TOKEN_EXPIRE_HOURS)
    if purpose == "reset":
        return timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    return timedelta(minutes=settings.LOGIN_TOKEN_EXPIRE_MINUTES)


def _base_url(purpose: str) -> str:
    # Le lien de reset ouvre la page « nouveau mot de passe », pas la page de vérification
    return settings.FRONTEND_RESET_URL if purpose == "reset" else settings.FRONTEND_VERIFY_URL


def create_verification_link(db, user, purpose, attempt_secret=None) -> str:
    now = datetime.now(timezone.utc)

    # Annule les anciens liens non utilisés (même user, même purpose)
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
    ttl = _ttl(purpose)

    db.add(EmailVerification(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(raw),
        # secret de la page de login : seul son hash est stocké (None pour signup et reset)
        attempt_hash=hash_token(attempt_secret) if attempt_secret else None,
        expires_at=now + ttl,
    ))
    logger.info("Lien de vérification créé pour %s (purpose=%s, expire à %s)", user.username, purpose, now + ttl)
    db.commit()

    return f"{_base_url(purpose)}?token={raw}"


def discard_pending_links(db, user, purpose) -> None:
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
