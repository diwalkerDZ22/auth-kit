import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.cookies import clear_refresh_cookie, read_refresh_cookie, require_csrf
from app.core.errors import ApiError
from app.core.limiter import limiter
from app.core.password_policy import password_problem
from app.core.security import decode_access_token, verify_password
from app.core.tokens import issue_session
from app.crud.user import bump_token_version, get_user_by_username, set_password
from app.db.base import get_db
from app.schemas.user import AccessToken, PasswordChange, UserMe, UserUpdate
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
    # Version différente : token révoqué (logout, mot de passe, désactivation, rôle)
    if user is None or payload.get("ver") != user.token_version:
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


def new_password_error(user: User, new_password: str, field: str = "new_password") -> ApiError | None:
    """Erreur 422 au même format que la validation Pydantic, ou None si le mot de passe convient."""
    problem = password_problem(new_password, user.username, user.email)
    if problem:
        return ApiError("validation_error", fields={field: problem})
    return None


@router.post("/logout", dependencies=[Depends(require_csrf)])
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    # Par le cookie : marche aussi quand l'access token a expiré
    refresh_token = read_refresh_cookie(request)
    payload = decode_access_token(refresh_token) if refresh_token else None
    if payload and payload.get("type") == "refresh":
        user = get_user_by_username(db, payload.get("sub") or "")
        if user and user.refresh_token == refresh_token:
            bump_token_version(user)   # révoque aussi les access tokens en cours
            db.commit()
            logger.info("Déconnexion de l'utilisateur %s", user.username)
    clear_refresh_cookie(response)
    return {"message": "Déconnexion réussie."}


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_active_user)):
    return UserMe.from_user(user)


@router.patch("/me", response_model=UserMe)
def update_me(
    payload: UserUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if "full_name" in payload.model_fields_set:
        user.full_name = payload.full_name or None
    db.commit()
    logger.info("Profil mis à jour pour %s", user.username)
    return UserMe.from_user(user)


@router.post("/password/change", response_model=AccessToken)
@limiter.limit("5/15minutes")   # vérifie le mot de passe actuel : même protection que /token
def change_password(
    request: Request,
    response: Response,
    payload: PasswordChange,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.current_password, user.hashed_password):
        logger.info("Changement de mot de passe refusé à %s : mot de passe actuel faux", user.username)
        raise ApiError("invalid_current_password")
    if payload.new_password == payload.current_password:
        raise ApiError("validation_error", fields={"new_password": "Le nouveau mot de passe doit être différent de l'actuel."})
    error = new_password_error(user, payload.new_password)
    if error:
        raise error

    # Coupe les autres sessions, puis rouvre celle-ci avec des tokens neufs
    set_password(user, payload.new_password)
    db.commit()
    logger.info("Mot de passe changé pour %s", user.username)
    return issue_session(db, user, response)
