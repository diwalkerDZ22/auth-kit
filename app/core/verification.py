# app/core/verification.py
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.db.models import EmailVerification


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


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

    ttl = (
        timedelta(hours=settings.SIGNUP_TOKEN_EXPIRE_HOURS)
        if purpose == "signup"
        else timedelta(minutes=settings.LOGIN_TOKEN_EXPIRE_MINUTES)
    )

    db.add(EmailVerification(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(raw),
        # secret de la page de login : seul son hash est stocké (None pour signup)
        attempt_hash=hash_token(attempt_secret) if attempt_secret else None,
        expires_at=now + ttl,
    ))
    print(f"Verification link created for user {user.username} with purpose {purpose}. Expires at {now + ttl}.")
    db.commit()

    return f"{settings.FRONTEND_VERIFY_URL}?token={raw}"