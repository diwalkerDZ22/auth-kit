"""Mot de passe : oublié (lien par email), réinitialisation, changement."""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from auth_kit.context import KitContext
from auth_kit.errors import ApiError
from auth_kit.models import User
from auth_kit.passwords import new_password_error
from auth_kit.ports import EmailMessage
from auth_kit.security import verify_password
from auth_kit.services.accounts import get_user_by_email, set_password
from auth_kit.services.verification import create_link, find_active_link, sent_recently
from auth_kit.templates import render_link_email

logger = logging.getLogger(__name__)


def forgot_password(db: Session, ctx: KitContext, email: str) -> EmailMessage | None:
    """Mail à envoyer, ou None. L'appelant répond la même chose dans tous les cas."""
    user = get_user_by_email(db, email)
    if not user or user.disabled:
        return None
    if sent_recently(db, user, "reset", ctx.settings.link_email_cooldown_seconds):
        return None
    link = create_link(db, ctx, user, "reset")
    logger.info("Lien de réinitialisation programmé pour %s", user.username)
    return render_link_email(ctx.templates, ctx.settings.app_name, user.email, link, "reset")


def reset_password(db: Session, ctx: KitContext, token: str, new_password: str) -> User:
    verification = find_active_link(db, token, ("reset",))
    if not verification:
        logger.info("Lien de réinitialisation invalide ou expiré")
        raise ApiError("invalid_link")

    user = verification.user
    if user.disabled:
        raise ApiError("account_disabled")
    # Lien non consommé si le mot de passe est refusé : l'utilisateur peut réessayer
    if error := new_password_error(ctx, user.username, user.email, new_password, field="new_password"):
        raise error

    verification.used_at = datetime.now(timezone.utc)
    set_password(user, new_password)   # révoque aussi toutes les sessions
    user.is_verified = True            # cliquer le lien prouve la possession de l'email
    db.commit()
    logger.info("Mot de passe réinitialisé pour %s", user.username)
    return user


def change_password(db: Session, ctx: KitContext, user: User, current_password: str, new_password: str) -> None:
    """Coupe toutes les sessions (celle-ci comprise) : l'appelant en rouvre une pour cet appareil."""
    if not verify_password(current_password, user.hashed_password):
        logger.info("Changement de mot de passe refusé à %s : mot de passe actuel faux", user.username)
        raise ApiError("invalid_current_password")
    if new_password == current_password:
        raise ApiError("validation_error", fields={"new_password": "Le nouveau mot de passe doit être différent de l'actuel."})
    if error := new_password_error(ctx, user.username, user.email, new_password, field="new_password"):
        raise error
    set_password(user, new_password)
    db.commit()
    logger.info("Mot de passe changé pour %s", user.username)
