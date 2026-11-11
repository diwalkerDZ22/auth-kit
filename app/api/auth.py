import logging

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import decode_access_token
from app.crud.user import get_user_by_username, revoke_refresh_token
from app.db.base import get_db
from app.schemas.user import UserMe
from app.db.models import User


router = APIRouter()
bearer_scheme = HTTPBearer()
logger = logging.getLogger(__name__)

_BEARER = {"WWW-Authenticate": "Bearer"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    payload = decode_access_token(credentials.credentials)
    # Refuse les refresh tokens (et tout autre token) utilisés comme access token
    if payload is None or payload.get("type") != "access":
        raise ApiError("invalid_token", headers=_BEARER)

    username = payload.get("sub")
    if username is None:
        raise ApiError("invalid_token", headers=_BEARER)

    user = get_user_by_username(db, username)
    if user is None:
        raise ApiError("invalid_token", headers=_BEARER)
    return user


def get_current_active_user(user: User = Depends(get_current_user)):
    if user.disabled:
        raise ApiError("account_disabled")
    if not user.is_verified:
        raise ApiError("email_not_verified")
    return user

def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_active_user)):
        if permission not in {p.code for p in user.role.permissions}:
            raise ApiError("permission_denied")
        return user
    return dependency


@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    revoke_refresh_token(db, current_user.id)
    logger.info("Déconnexion de l'utilisateur %s", current_user.username)
    return {"message": "Déconnexion réussie."}


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_active_user)):
    return UserMe(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_verified=user.is_verified,
        role=user.role.name,
        permissions=sorted(p.code for p in user.role.permissions),
    )
