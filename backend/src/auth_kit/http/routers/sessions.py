"""Refresh et déconnexion (toujours actifs) ; appareils connectés (fonctionnalité "devices")."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.errors import ApiError
from auth_kit.http.cookies import clear_cookie_headers, clear_refresh_cookie, read_refresh_cookie, require_csrf
from auth_kit.http.deps import AuthDependencies, client_info
from auth_kit.http.responses import session_response
from auth_kit.http.schemas import AccessToken, MessageOut, RevokeOthersOut, RevokeOut, SessionOut
from auth_kit.models import User
from auth_kit.services import sessions as service


def build_session_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["sessions"])
    settings = ctx.settings

    @router.post(
        "/refresh",
        response_model=AccessToken,
        dependencies=[Depends(require_csrf), Depends(deps.rate_limit("refresh"))],
    )
    def refresh(request: Request, response: Response, db: Session = Depends(deps.get_db)):
        # Le refresh token vient du cookie httpOnly, jamais du corps
        raw = read_refresh_cookie(settings, request)
        result = service.refresh_session(db, ctx, raw, client_info(request)) if raw else None
        if result is None or result.issued is None:
            code = result.error if result else "invalid_refresh_token"
            raise ApiError(code, headers=clear_cookie_headers(settings))
        return session_response(settings, response, result.issued)

    @router.post("/logout", response_model=MessageOut, dependencies=[Depends(require_csrf)])
    def logout(request: Request, response: Response, db: Session = Depends(deps.get_db)):
        """Ferme la session de cet appareil. Par le cookie : marche aussi quand l'access token a expiré."""
        raw = read_refresh_cookie(settings, request)
        if raw:
            service.logout(db, raw)
        clear_refresh_cookie(settings, response)
        return MessageOut(message="Déconnexion réussie.")

    return router


def build_devices_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["sessions"])

    @router.get("/sessions", response_model=list[SessionOut])
    def list_sessions(
        payload: dict = Depends(deps.token_payload),
        user: User = Depends(deps.current_active_user),
        db: Session = Depends(deps.get_db),
    ):
        return [SessionOut.from_session(s, current_id=payload["sid"]) for s in service.active_sessions(db, user)]

    @router.delete("/sessions/{session_id}", response_model=RevokeOut)
    def revoke_one(
        session_id: str,
        payload: dict = Depends(deps.token_payload),
        user: User = Depends(deps.current_active_user),
        db: Session = Depends(deps.get_db),
    ):
        """Déconnecte un appareil. Pour l'appareil courant, préférer /logout (efface le cookie)."""
        session = service.revoke_user_session(db, user, session_id)
        if session is None:
            raise ApiError("session_not_found")
        return RevokeOut(message="Appareil déconnecté.", current=session.id == payload["sid"])

    @router.delete("/sessions", response_model=RevokeOthersOut)
    def revoke_others(
        payload: dict = Depends(deps.token_payload),
        user: User = Depends(deps.current_active_user),
        db: Session = Depends(deps.get_db),
    ):
        """Déconnecte tous les autres appareils ; la session courante reste ouverte."""
        count = service.revoke_other_sessions(db, user, payload["sid"])
        return RevokeOthersOut(message="Les autres appareils ont été déconnectés.", count=count)

    return router
