"""Nettoyage des liens email et des sessions qui ne servent plus (à planifier : cron, tâche de fond)."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth_kit.models import EmailVerification, UserSession


def cleanup(db: Session, keep_days: int = 7, now: datetime | None = None) -> tuple[int, int]:
    """Renvoie (liens supprimés, sessions supprimées)."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=keep_days)

    # Liens expirés depuis plus de keep_days (utilisés ou non)
    links = (
        db.query(EmailVerification)
        .filter(EmailVerification.expires_at < cutoff)
        .delete(synchronize_session=False)
    )
    # Sessions expirées, ou fermées depuis plus de keep_days
    sessions = (
        db.query(UserSession)
        .filter(or_(UserSession.expires_at < now, UserSession.revoked_at < cutoff))
        .delete(synchronize_session=False)
    )
    db.commit()
    return links, sessions
