import logging
from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import clear_cookie_headers, read_refresh_cookie, require_csrf
from app.core.email import send_verification_email
from app.core.errors import ApiError
from app.core.limiter import limiter
from app.core.security import decode_access_token
from app.core.tokens import issue_session
from app.core.verification import create_verification_link, discard_pending_links, hash_token
from app.crud.user import (
    authenticate_user,
    get_user_by_username,
)
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import AccessToken, ClaimRequest

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/token", response_model=None)       # plus TokenPair : la réponse change selon le cas
@limiter.limit("10/15minutes")   # anti brute-force du mot de passe
def login(
    request: Request,
    response: Response,
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
        return issue_session(db, user, response)

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
    # Envoi synchrone : on ne répond « mail envoyé » que s'il est vraiment parti
    if not send_verification_email(user.email, link, "login"):
        discard_pending_links(db, user, "login")
        logger.warning("Email de login non envoyé pour %s", user.username)
        raise ApiError("email_unavailable")
    logger.info("Email de login envoyé pour %s", user.username)

    return JSONResponse(
        status_code=202,
        content={
            "code": "login_email_sent",
            "attempt_id": attempt_secret,
            "message": "Un lien de connexion vient d'être envoyé à votre adresse email.",
        },
    )

@router.post("/refresh", response_model=AccessToken, dependencies=[Depends(require_csrf)])
@limiter.limit("30/minute")
def refresh_access_token(request: Request, response: Response, db: Session = Depends(get_db)):
    # Le refresh token vient du cookie httpOnly, jamais du corps
    refresh_token = read_refresh_cookie(request)
    payload = decode_access_token(refresh_token) if refresh_token else None
    if payload is None or payload.get("type") != "refresh":
        raise ApiError("invalid_refresh_token", headers=clear_cookie_headers())

    username = payload.get("sub")
    user = get_user_by_username(db, username)

    # Seul le dernier refresh token émis est valable, et sa version doit être à jour
    if user is None or user.refresh_token != refresh_token or payload.get("ver") != user.token_version:
        raise ApiError("invalid_refresh_token", headers=clear_cookie_headers())

    if user.disabled or not user.is_verified:
        logger.info("Refresh refusé à %s : compte désactivé ou non vérifié", user.username)
        raise ApiError("account_not_allowed", headers=clear_cookie_headers())

    logger.info("Refresh des tokens pour %s", user.username)
    return issue_session(db, user, response)


@router.post("/login/claim", response_model=None)
@limiter.limit("60/minute")   # route interrogée en boucle par la page de login
def claim_login(request: Request, response: Response, payload: ClaimRequest, db: Session = Depends(get_db)):
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
    return issue_session(db, user, response)
