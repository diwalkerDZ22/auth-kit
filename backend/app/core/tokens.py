from datetime import timedelta

from fastapi import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cookies import set_refresh_cookie
from app.core.security import create_access_token, create_refresh_token
from app.crud.user import save_refresh_token
from app.db.models import User


def issue_tokens(db: Session, user: User) -> dict:
    # "ver" = token_version : un token dont la version ne correspond plus est refusé
    claims = {"sub": user.username, "ver": user.token_version}
    access_token = create_access_token(
        data=claims,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    refresh_token = create_refresh_token(data=claims)
    save_refresh_token(db, user.id, refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


def issue_session(db: Session, user: User, response: Response) -> dict:
    """Ouvre une session : access token dans le corps, refresh token en cookie httpOnly."""
    tokens = issue_tokens(db, user)
    set_refresh_cookie(response, tokens["refresh_token"])
    return {
        "access_token": tokens["access_token"],
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
