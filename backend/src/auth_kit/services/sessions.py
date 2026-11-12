"""Sessions par appareil : ouverture, refresh (rotation), révocation.

Voir docs/Sprint7-Sessions-et-durcissement.md. Seul endroit où les tokens sont émis.
"""
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.models import User, UserSession
from auth_kit.security import create_access_token
from auth_kit.services.verification import hash_token

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClientInfo:
    ip: str | None = None
    user_agent: str | None = None

    def truncated(self) -> "ClientInfo":
        return ClientInfo(
            ip=self.ip[:64] if self.ip else None,
            user_agent=self.user_agent[:255] if self.user_agent else None,
        )


@dataclass(frozen=True)
class IssuedSession:
    access: dict                  # corps AccessToken
    refresh_token: str | None     # à poser en cookie ; None : garder le cookie actuel


def _access_body(ctx: KitContext, user: User, session: UserSession) -> dict:
    # sub = id (le username peut changer), ver = token_version, sid = session
    access_token = create_access_token(
        ctx.settings, {"sub": str(user.id), "ver": user.token_version, "sid": session.id}
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ctx.settings.access_token_expire_minutes * 60,
    }


def open_session(db: Session, ctx: KitContext, user: User, client: ClientInfo) -> IssuedSession:
    now = datetime.now(timezone.utc)
    raw = secrets.token_urlsafe(32)
    client = client.truncated()
    session = UserSession(
        id=secrets.token_urlsafe(16),
        user_id=user.id,
        token_hash=hash_token(raw),
        ip=client.ip,
        user_agent=client.user_agent,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=ctx.settings.refresh_token_expire_days),
    )
    db.add(session)
    db.commit()
    return IssuedSession(access=_access_body(ctx, user, session), refresh_token=raw)


@dataclass(frozen=True)
class RefreshResult:
    issued: IssuedSession | None = None
    error: str | None = None        # code ApiError si le refresh est refusé


_INVALID = RefreshResult(error="invalid_refresh_token")


def _check_account(session: UserSession) -> RefreshResult | None:
    user = session.user
    if user.disabled or not user.is_verified:
        logger.info("Refresh refusé à %s : compte désactivé ou non vérifié", user.username)
        return RefreshResult(error="account_not_allowed")
    return None


def refresh_session(db: Session, ctx: KitContext, raw: str, client: ClientInfo) -> RefreshResult:
    """Échange le refresh token du cookie contre un access token neuf.

    - Token courant : rotation (nouveau cookie), session prolongée.
    - Token précédent, remplacé il y a moins de refresh_reuse_grace_seconds : requête
      concurrente d'un autre onglet. Access token neuf, cookie inchangé.
    - Token précédent, plus vieux : réutilisation d'un token volé probable -> session révoquée.
    """
    now = datetime.now(timezone.utc)
    hashed = hash_token(raw)
    s = ctx.settings

    session = db.query(UserSession).filter(UserSession.token_hash == hashed).with_for_update().first()
    if session is not None:
        if session.revoked_at is not None or session.expires_at <= now:
            return _INVALID
        if refused := _check_account(session):
            return refused
        new_raw = secrets.token_urlsafe(32)
        client = client.truncated()
        session.previous_token_hash = session.token_hash
        session.token_hash = hash_token(new_raw)
        session.rotated_at = now
        session.last_used_at = now
        session.ip, session.user_agent = client.ip, client.user_agent
        session.expires_at = now + timedelta(days=s.refresh_token_expire_days)
        db.commit()
        return RefreshResult(issued=IssuedSession(_access_body(ctx, session.user, session), new_raw))

    session = db.query(UserSession).filter(UserSession.previous_token_hash == hashed).with_for_update().first()
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return _INVALID
    if session.rotated_at and now - session.rotated_at <= timedelta(seconds=s.refresh_reuse_grace_seconds):
        if refused := _check_account(session):
            return refused
        return RefreshResult(issued=IssuedSession(_access_body(ctx, session.user, session), None))

    session.revoked_at = now
    db.commit()
    logger.warning("Refresh token déjà remplacé réutilisé : session %s de %s révoquée", session.id, session.user.username)
    return _INVALID


def find_session_by_token(db: Session, raw: str) -> UserSession | None:
    """Session du cookie (token courant, ou précédent pendant le délai de grâce)."""
    hashed = hash_token(raw)
    session = db.query(UserSession).filter(UserSession.token_hash == hashed).first()
    if session is None:
        session = db.query(UserSession).filter(UserSession.previous_token_hash == hashed).first()
    return session


def revoke_session(session: UserSession) -> None:
    """Le commit reste à l'appelant."""
    if session.revoked_at is None:
        session.revoked_at = datetime.now(timezone.utc)


def is_active(session: UserSession | None) -> bool:
    return (
        session is not None
        and session.revoked_at is None
        and session.expires_at > datetime.now(timezone.utc)
    )


def active_sessions(db: Session, user: User) -> list[UserSession]:
    now = datetime.now(timezone.utc)
    return (
        db.query(UserSession)
        .filter(UserSession.user_id == user.id, UserSession.revoked_at.is_(None), UserSession.expires_at > now)
        .order_by(UserSession.last_used_at.desc())
        .all()
    )


def logout(db: Session, raw: str) -> UserSession | None:
    session = find_session_by_token(db, raw)
    if session is not None and session.revoked_at is None:
        revoke_session(session)
        db.commit()
        logger.info("Déconnexion de %s (session %s)", session.user.username, session.id)
        return session
    return None


def revoke_user_session(db: Session, user: User, session_id: str) -> UserSession | None:
    """Ferme une session du compte. None si inconnue, déjà fermée ou d'un autre compte."""
    session = db.get(UserSession, session_id)
    if session is None or session.user_id != user.id or session.revoked_at is not None:
        return None
    revoke_session(session)
    db.commit()
    logger.info("Session %s de %s fermée à distance", session.id, user.username)
    return session


def revoke_other_sessions(db: Session, user: User, keep_session_id: str) -> int:
    others = [s for s in active_sessions(db, user) if s.id != keep_session_id]
    for session in others:
        revoke_session(session)
    db.commit()
    logger.info("%s a fermé %d autre(s) session(s)", user.username, len(others))
    return len(others)
