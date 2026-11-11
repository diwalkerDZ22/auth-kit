import logging
from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_verification_email
from app.core.errors import ApiError
from app.core.limiter import limiter
from app.core.security import decode_access_token
from app.core.tokens import issue_tokens
from app.core.verification import create_verification_link, hash_token
from app.crud.user import (
    authenticate_user,
    get_user_by_username,
)
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import ClaimRequest, RefreshRequest, TokenPair

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/token", response_model=None)       # plus TokenPair : la réponse change selon le cas
@limiter.limit("10/15minutes")   # anti brute-force du mot de passe
def login(
    request: Request,
    background: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.info("Échec de connexion pour le username %r", form_data.username)
        raise ApiError("invalid_credentials", headers={"WWW-Authenticate": "Bearer"})
    if user.disabled:
        logger.info("Connexion refusée à %s : compte désactivé", user.username)
        raise ApiError("account_disabled")
    if not user.is_verified:
        logger.info("Connexion refusée à %s : email non vérifié", user.username)
        raise ApiError("email_not_verified")

    # Mode dev : pas d'étape email (Swagger)
    if not settings.LOGIN_EMAIL_REQUIRED:
        logger.info("Étape email de login ignorée pour %s (mode dev)", user.username)
        return issue_tokens(db, user)

    # Anti-spam : un seul email de login par minute
    last = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == "login")
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if last and now - last.created_at < timedelta(seconds=60):
        logger.info("Email de login redemandé trop tôt par %s", user.username)
        raise ApiError("login_email_cooldown")

    attempt_secret = secrets.token_urlsafe(32)
    link = create_verification_link(db, user, "login", attempt_secret)
    background.add_task(send_verification_email, user.email, link, "login")
    logger.info("Email de login programmé pour %s", user.username)

    return JSONResponse(
        status_code=202,
        content={
            "code": "login_email_sent",
            "attempt_id": attempt_secret,
            "message": "Un lien de connexion vient d'être envoyé à votre adresse email.",
        },
    )

@router.post("/refresh", response_model=TokenPair)
@limiter.limit("30/minute")
def refresh_access_token(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    payload = decode_access_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise ApiError("invalid_refresh_token")

    username = payload.get("sub")
    user = get_user_by_username(db, username)

    # Seul le dernier refresh token émis est valable
    if user is None or user.refresh_token != body.refresh_token:
        raise ApiError("invalid_refresh_token")

    if user.disabled or not user.is_verified:
        logger.info("Refresh refusé à %s : compte désactivé ou non vérifié", user.username)
        raise ApiError("account_not_allowed")

    logger.info("Refresh des tokens pour %s", user.username)
    return issue_tokens(db, user)


@router.post("/login/claim", response_model=None)
@limiter.limit("60/minute")   # route interrogée en boucle par la page de login
def claim_login(request: Request, payload: ClaimRequest, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)

    v = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.attempt_hash == hash_token(payload.attempt_id),
            EmailVerification.purpose == "login",
            EmailVerification.claimed_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if not v:
        raise ApiError("login_attempt_unknown")

    # Pas encore approuvée
    if v.approved_at is None:
        if v.used_at is not None or v.expires_at <= now:
            # lien remplacé par un plus récent, ou expiré
            raise ApiError("login_link_expired")
        return JSONResponse(
            status_code=202,
            content={"code": "login_pending", "message": "En attente de la confirmation par email."},
        )

    # Approuvée, mais trop tard pour récupérer les tokens
    if now - v.approved_at > timedelta(minutes=2):
        raise ApiError("login_approval_expired")

    user = v.user
    if not user.is_verified or user.disabled:
        raise ApiError("account_not_allowed")

    v.claimed_at = now
    db.commit()
    logger.info("Tokens remis à la page de login de %s", user.username)
    return issue_tokens(db, user)
