"""Compte de l'utilisateur connecté : profil et changement de mot de passe."""
import logging

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.http.deps import AuthDependencies, client_info
from auth_kit.http.responses import session_response
from auth_kit.http.schemas import AccessToken, PasswordChange, UserMe, UserUpdate
from auth_kit.models import User
from auth_kit.services.recovery import change_password
from auth_kit.services.sessions import open_session

logger = logging.getLogger(__name__)


def build_account_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["compte"])

    @router.get("/me", response_model=UserMe)
    def me(user: User = Depends(deps.current_active_user)):
        return UserMe.from_user(user)

    @router.patch("/me", response_model=UserMe)
    def update_me(
        payload: UserUpdate,
        user: User = Depends(deps.current_active_user),
        db: Session = Depends(deps.get_db),
    ):
        if "full_name" in payload.model_fields_set:
            user.full_name = payload.full_name or None
        db.commit()
        logger.info("Profil mis à jour pour %s", user.username)
        return UserMe.from_user(user)

    @router.post(
        "/password/change",
        response_model=AccessToken,
        dependencies=[Depends(deps.rate_limit("change_password"))],
    )
    def change(
        request: Request,
        response: Response,
        payload: PasswordChange,
        user: User = Depends(deps.current_active_user),
        db: Session = Depends(deps.get_db),
    ):
        # Coupe toutes les sessions (autres appareils compris), puis en rouvre une pour cet appareil
        change_password(db, ctx, user, payload.current_password, payload.new_password)
        return session_response(ctx.settings, response, open_session(db, ctx, user, client_info(request)))

    return router
