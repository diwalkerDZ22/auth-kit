# app/core/verification.py
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EmailVerification, User


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def create_verification_link(db: Session, user: User, purpose: str) -> str:
    now = datetime.now(timezone.utc)

    # 3. Invalider les tokens non utilisés du même (user, purpose)
    (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user.id,
            EmailVerification.purpose == purpose,
            EmailVerification.used_at.is_(None),
        )
        .update({"used_at": now}, synchronize_session=False)
    )

    # 1-2. Token brut + hash
    raw = secrets.token_urlsafe(32)

    # 4. Durée selon le purpose
    ttl = (
        timedelta(hours=settings.signup_token_expire_hours)
        if purpose == "signup"
        else timedelta(minutes=settings.login_token_expire_minutes)
    )

    db.add(EmailVerification(
        user_id=user.id,
        purpose=purpose,
        token_hash=hash_token(raw),
        expires_at=now + ttl,
    ))
    db.commit()

    # 5. Le lien
    return f"{settings.frontend_verify_url}?token={raw}"