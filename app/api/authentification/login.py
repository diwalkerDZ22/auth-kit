import logging
from datetime import datetime, timedelta, timezone
import secrets
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_verification_email
from app.core.security import decode_access_token
from app.core.tokens import issue_tokens
from app.core.verification import create_verification_link
from app.crud.user import (
    authenticate_user,
    get_user_by_username,
)
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import ClaimRequest, RefreshRequest, TokenPair, ClaimRequest
from app.core.verification import hash_token

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/token", response_model=None)       # plus TokenPair : la réponse change selon le cas
def login(
    background: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        print(f"Failed login attempt for username: {form_data.username}")
        raise HTTPException(status_code=401, detail="Incorrect username or password",
                            headers={"WWW-Authenticate": "Bearer"})
    if user.disabled:
        print(f"User {user.username} attempted to login but account is disabled.")
        raise HTTPException(status_code=403, detail="Compte désactivé")
    if not user.is_verified:
        print(f"User {user.username} attempted to login but email is not verified.")
        raise HTTPException(
            status_code=403,
            detail={"code": "email_not_verified",
                    "message": "Vérifiez votre email avant de vous connecter."},
        )

    # Mode dev : pas d'étape email (Swagger)
    if not settings.LOGIN_EMAIL_REQUIRED:
        print(f"Login email step skipped for user {user.username} (dev mode).")
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
        print(f"User {user.username} attempted to request a login email too soon after the last one.")
        raise HTTPException(status_code=429,
                            detail="Un email vient d'être envoyé, patientez un instant.")

    attempt_secret = secrets.token_urlsafe(32)
    link = create_verification_link(db, user, "login", attempt_secret)
    background.add_task(send_verification_email, user.email, link, "login")
    print(f"Login email sent to user {user.username} at {user.email}. Link expires at {now + timedelta(minutes=settings.LOGIN_TOKEN_EXPIRE_MINUTES)}.")

    return JSONResponse(
        status_code=202,
        content={
            "code": "login_email_sent",
            "attempt_id": attempt_secret,
            "message": "Un lien de connexion vient d'être envoyé à votre adresse email.",
        },
    )

@router.post("/refresh", response_model=TokenPair)
def refresh_access_token(body: RefreshRequest, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid refresh token",
    )

    payload = decode_access_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise credentials_exception

    username = payload.get("sub")
    user = get_user_by_username(db, username)

    if user is None or user.refresh_token != body.refresh_token:
        raise credentials_exception
    
    if user.disabled or not user.is_verified:
        print(f"User {user.username} attempted to refresh token but account is disabled or not verified.")
        raise HTTPException(status_code=403, detail="Compte non autorisé")

    print(f"Refresh token used for user {user.username}. Issuing new access token.")
    return issue_tokens(db, user)

from app.core.verification import hash_token

@router.post("/login/claim", response_model=None)
def claim_login(payload: ClaimRequest, db: Session = Depends(get_db)):
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
        raise HTTPException(status_code=410, detail="Tentative inconnue ou déjà utilisée")

    # Pas encore approuvée
    if v.approved_at is None:
        if v.used_at is not None or v.expires_at <= now:
            # lien remplacé par un plus récent, ou expiré
            raise HTTPException(status_code=410, detail="Lien expiré, recommencez la connexion")
        return JSONResponse(status_code=202, content={"status": "pending"})

    # Approuvée, mais trop tard pour récupérer les tokens
    if now - v.approved_at > timedelta(minutes=2):
        raise HTTPException(status_code=410, detail="Approbation expirée, recommencez la connexion")

    user = v.user
    if not user.is_verified or user.disabled:
        raise HTTPException(status_code=403, detail="Compte non vérifié ou désactivé")

    v.claimed_at = now
    db.commit()
    return issue_tokens(db, user)