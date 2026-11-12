"""Dépendances FastAPI, liées à un AuthKit (sa config et la session SQLAlchemy du projet).

    @router.get("/jobs", dependencies=[Depends(kit.require_permission("jobs:read"))])
    def jobs(user: User = Depends(kit.current_user)): ...
"""
from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.errors import ApiError
from auth_kit.models import User, UserSession
from auth_kit.security import decode_access_token
from auth_kit.services.sessions import ClientInfo, is_active

_BEARER = {"WWW-Authenticate": "Bearer"}


def client_info(request: Request) -> ClientInfo:
    """IP et navigateur de la requête (IP du proxy si uvicorn n'a pas --proxy-headers)."""
    return ClientInfo(
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@dataclass(frozen=True)
class AuthDependencies:
    get_db: Callable
    token_payload: Callable
    current_user: Callable          # compte du token, même désactivé ou non vérifié
    current_active_user: Callable   # compte actif et vérifié (à utiliser par défaut)
    require_permission: Callable[[str], Callable]
    rate_limit: Callable[..., Callable]


def make_dependencies(ctx: KitContext, get_db: Callable) -> AuthDependencies:
    # auto_error=False : l'absence de token lève une ApiError, au format du kit même sur les routes du projet
    bearer_scheme = HTTPBearer(auto_error=False)

    def token_payload(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> dict:
        """Claims de l'access token. Refuse les tokens absents, invalides, expirés ou d'un autre type."""
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise ApiError("not_authenticated", headers=_BEARER)
        payload = decode_access_token(ctx.settings, credentials.credentials)
        if payload is None:
            raise ApiError("invalid_token", headers=_BEARER)
        return payload

    def current_user(payload: dict = Depends(token_payload), db: Session = Depends(get_db)) -> User:
        try:
            user = db.get(User, int(payload["sub"]))
        except (TypeError, ValueError):
            user = None
        # Version différente : tous les tokens du compte sont révoqués (mot de passe, désactivation, rôle)
        if user is None or payload.get("ver") != user.token_version:
            raise ApiError("invalid_token", headers=_BEARER)
        # Session fermée (déconnexion de cet appareil) ou expirée
        session = db.get(UserSession, payload["sid"])
        if not is_active(session) or session.user_id != user.id:
            raise ApiError("invalid_token", headers=_BEARER)
        return user

    def current_active_user(user: User = Depends(current_user)) -> User:
        if user.disabled:
            raise ApiError("account_disabled")
        if not user.is_verified:
            raise ApiError("email_not_verified")
        return user

    def require_permission(permission: str) -> Callable:
        def dependency(user: User = Depends(current_active_user)) -> User:
            if permission not in {p.code for p in user.role.permissions}:
                raise ApiError("permission_denied")
            return user
        return dependency

    def rate_limit(name: str, limit: str | None = None) -> Callable:
        """Limite par IP : à mettre dans dependencies=[...]. Sans limit : ctx.settings.rate_limit(name)."""
        limit = limit or ctx.settings.rate_limit(name)

        def dependency(request: Request) -> None:
            ip = request.client.host if request.client else "inconnue"
            if not ctx.limiter.hit(limit, "ip", name, ip):
                raise ApiError("rate_limited")
        return dependency

    return AuthDependencies(
        get_db=get_db,
        token_payload=token_payload,
        current_user=current_user,
        current_active_user=current_active_user,
        require_permission=require_permission,
        rate_limit=rate_limit,
    )
