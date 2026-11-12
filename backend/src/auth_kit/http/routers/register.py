"""Inscription publique et renvoi du mail de vérification (fonctionnalité "register")."""
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.http.deps import AuthDependencies
from auth_kit.http.schemas import EmailRequest, MessageOut, UserCreate
from auth_kit.services import accounts as service

REGISTER_MESSAGE = "Un email vient d'être envoyé à cette adresse : suivez ses instructions pour continuer."
RESEND_MESSAGE = "Si un compte non vérifié existe pour cette adresse, un email a été envoyé."


def build_register_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["inscription"])

    @router.post(
        "/register",
        response_model=MessageOut,
        status_code=201,
        dependencies=[Depends(deps.rate_limit("register"))],
    )
    def register(user_in: UserCreate, background: BackgroundTasks, db: Session = Depends(deps.get_db)):
        """Même réponse que l'email soit libre ou déjà inscrit : l'inscription ne révèle pas les comptes."""
        outcome = service.register(
            db, ctx,
            username=user_in.username,
            email=user_in.email,
            password=user_in.password,
            full_name=user_in.full_name,
        )
        for message in outcome.emails:
            background.add_task(ctx.email.send, message)
        return MessageOut(message=REGISTER_MESSAGE)

    @router.post("/resend-verification", response_model=MessageOut, dependencies=[Depends(deps.rate_limit("resend"))])
    def resend_verification(payload: EmailRequest, background: BackgroundTasks, db: Session = Depends(deps.get_db)):
        message = service.resend_verification(db, ctx, payload.email)
        if message is not None:
            background.add_task(ctx.email.send, message)
        # Même réponse dans tous les cas : ne révèle pas si le compte existe
        return MessageOut(message=RESEND_MESSAGE)

    return router
