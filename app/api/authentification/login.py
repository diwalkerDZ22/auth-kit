import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_verification_email
from app.core.security import create_access_token, create_refresh_token, decode_access_token
from app.core.verification import create_verification_link
from app.crud.user import (
    authenticate_user,
    get_user_by_username,
    revoke_refresh_token,
    save_refresh_token,
)
from app.db.base import get_db
from app.db.models import EmailVerification, User
from app.schemas.user import RefreshRequest, TokenPair


router = APIRouter()
logger = logging.getLogger(__name__)


def issue_tokens(db: Session, user: User) -> dict:
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data={"sub": user.username})
    save_refresh_token(db, user.id, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/token", response_model=None)
def login(
    background: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.disabled:
        logger.info("Login refusé (compte désactivé): %s", user.username)
        raise HTTPException(status_code=403, detail="Compte désactivé")
    if not user.is_verified:
        logger.info("Login refusé (email non vérifié): %s", user.username)
        raise HTTPException(
            status_code=403,
            detail={
                "code": "email_not_verified",
                "message": "Vérifiez votre email avant de vous connecter.",
            },
        )

    if not settings.LOGIN_EMAIL_REQUIRED:
        return issue_tokens(db, user)

    last = (
        db.query(EmailVerification)
        .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == "login")
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if not last or now - last.created_at > timedelta(seconds=60):
        link = create_verification_link(db, user, "login")
        background.add_task(send_verification_email, user.email, link, "login")

    return JSONResponse(
        status_code=202,
        content={
            "code": "login_email_sent",
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

    return issue_tokens(db, user)
