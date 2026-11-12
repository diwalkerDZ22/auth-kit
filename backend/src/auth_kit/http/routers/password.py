"""Mot de passe oublié : lien par email, puis nouveau mot de passe (fonctionnalité "password_reset")."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.http.deps import AuthDependencies
from auth_kit.http.schemas import EmailRequest, MessageOut, PasswordReset
from auth_kit.services import recovery as service


def build_password_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["mot de passe"])

    @router.post("/password/forgot", response_model=MessageOut, dependencies=[Depends(deps.rate_limit("forgot"))])
    def forgot_password(payload: EmailRequest, background: BackgroundTasks, db: Session = Depends(deps.get_db)):
        message = service.forgot_password(db, ctx, payload.email)
        if message is not None:
            background.add_task(ctx.email.send, message)
        # Même réponse dans tous les cas : ne révèle pas si le compte existe
        return MessageOut(message="Si un compte existe pour cette adresse, un email de réinitialisation a été envoyé.")

    @router.post("/password/reset", response_model=MessageOut, dependencies=[Depends(deps.rate_limit("reset"))])
    def reset_password(payload: PasswordReset, db: Session = Depends(deps.get_db)):
        service.reset_password(db, ctx, payload.token, payload.new_password)
        return MessageOut(message="Mot de passe modifié, vous pouvez vous connecter.")

    return router
