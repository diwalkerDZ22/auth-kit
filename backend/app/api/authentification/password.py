"""Mot de passe oublié : demande d'un lien par email, puis choix d'un nouveau mot de passe."""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session

from app.api.auth import new_password_error
from app.core.email import send_verification_email
from app.core.errors import ApiError
from app.core.limiter import limiter
from app.core.verification import create_verification_link, hash_token
from app.crud.user import get_user_by_email, set_password
from app.db.base import get_db
from app.db.models import EmailVerification
from app.schemas.user import ForgotPasswordRequest, PasswordReset

router = APIRouter()
logger = logging.getLogger(__name__)

_RESET_COOLDOWN = timedelta(minutes=2)


@router.post("/password/forgot")
@limiter.limit("3/15minutes")
def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    user = get_user_by_email(db, payload.email)

    if user and not user.disabled:
        last = (
            db.query(EmailVerification)
            .filter(EmailVerification.user_id == user.id, EmailVerification.purpose == "reset")
            .order_by(EmailVerification.created_at.desc())
            .first()
        )
        if not last or datetime.now(timezone.utc) - last.created_at > _RESET_COOLDOWN:
            link = create_verification_link(db, user, "reset")
            background.add_task(send_verification_email, user.email, link, "reset")
            logger.info("Lien de réinitialisation programmé pour %s", user.username)

    # Même réponse dans tous les cas : ne révèle pas si le compte existe
    return {"message": "Si un compte existe pour cette adresse, un email de réinitialisation a été envoyé."}


@router.post("/password/reset")
@limiter.limit("10/15minutes")
def reset_password(request: Request, payload: PasswordReset, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.token_hash == hash_token(payload.token),
            EmailVerification.purpose == "reset",
            EmailVerification.used_at.is_(None),
            EmailVerification.expires_at > now,
        )
        .with_for_update()
        .first()
    )
    if not verification:
        logger.info("Lien de réinitialisation invalide ou expiré")
        raise ApiError("invalid_link")

    user = verification.user
    if user.disabled:
        raise ApiError("account_disabled")

    # Lien non consommé si le mot de passe est refusé : l'utilisateur peut réessayer
    error = new_password_error(user, payload.new_password)
    if error:
        raise error

    verification.used_at = now
    set_password(user, payload.new_password)   # révoque aussi toutes les sessions
    user.is_verified = True                    # cliquer le lien prouve la possession de l'email
    db.commit()
    logger.info("Mot de passe réinitialisé pour %s", user.username)
    return {"message": "Mot de passe modifié, vous pouvez vous connecter."}
