"""Comptes : recherche, création, inscription, identification, révocation."""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from auth_kit.context import DEFAULT_ROLE, KitContext
from auth_kit.errors import ApiError
from auth_kit.models import Role, User
from auth_kit.passwords import new_password_error
from auth_kit.ports import EmailMessage
from auth_kit.security import burn_password_check, get_password_hash, verify_password
from auth_kit.services.verification import create_link, sent_recently
from auth_kit.templates import render_account_exists_email, render_link_email

logger = logging.getLogger(__name__)


def get_user(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    # Insensible à la casse : couvre aussi les comptes créés avant la normalisation
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def create_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
    full_name: str | None = None,
    role: str = DEFAULT_ROLE,
    verified: bool = False,
) -> User:
    """Crée un compte (aucune vérification de règles : voir register() pour le parcours public)."""
    role_row = db.query(Role).filter(Role.name == role).one()
    user = User(
        username=username,
        email=email.strip().lower(),
        full_name=full_name,
        hashed_password=get_password_hash(password),
        disabled=False,
        role_id=role_row.id,
        is_verified=verified,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user:
        burn_password_check()   # même durée qu'un mauvais mot de passe : ne révèle pas le username
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def revoke_all_sessions(user: User) -> None:
    """Coupe toutes les sessions du compte (access et refresh tokens). Le commit reste à l'appelant."""
    now = datetime.now(timezone.utc)
    user.token_version = (user.token_version or 0) + 1   # access tokens en cours
    for session in user.sessions:
        if session.revoked_at is None:
            session.revoked_at = now


def set_password(user: User, new_password: str) -> None:
    """Change le mot de passe, révoque les sessions et les liens en attente. Le commit reste à l'appelant.

    Les liens de login et de reset encore actifs sont annulés : une tentative lancée avec
    l'ancien mot de passe ne peut plus aboutir.
    """
    now = datetime.now(timezone.utc)
    user.hashed_password = get_password_hash(new_password)
    revoke_all_sessions(user)
    for link in user.email_verifications:
        if link.purpose in ("login", "reset") and link.used_at is None:
            link.used_at = now


# --- Inscription ----------------------------------------------------------------------------

@dataclass
class RegisterOutcome:
    emails: list[EmailMessage] = field(default_factory=list)   # à envoyer (en tâche de fond)


def register(
    db: Session,
    ctx: KitContext,
    *,
    username: str,
    email: str,
    password: str,
    full_name: str | None = None,
) -> RegisterOutcome:
    """Inscription publique. Même résultat visible que l'email soit libre ou déjà inscrit.

    Les règles statiques (format, longueur) sont validées en amont (schéma) ; ici :
    username pris, fuites connues, email déjà inscrit.
    """
    # Le username est public (il se choisit) : le dire pris est inévitable.
    if get_user_by_username(db, username):
        raise ApiError("username_taken")
    if error := new_password_error(ctx, username, email, password, field="password"):
        raise error

    s = ctx.settings
    existing = get_user_by_email(db, email)
    if existing:
        # L'email ne doit pas être révélé : même réponse, même durée, et le titulaire est prévenu
        get_password_hash(password)
        outcome = RegisterOutcome()
        if ctx.limiter.hit(s.account_exists_mail_limit, "account-exists-mail", existing.email):
            outcome.emails.append(render_account_exists_email(ctx.templates, s.app_name, existing.email))
        logger.info("Inscription avec l'email du compte existant %s : avis envoyé", existing.username)
        return outcome

    try:
        user = create_user(db, username=username, email=email, password=password, full_name=full_name)
    except IntegrityError:
        db.rollback()
        raise ApiError("account_exists")

    link = create_link(db, ctx, user, "signup")
    logger.info("Inscription de %s (id=%s), email de vérification programmé", user.username, user.id)
    return RegisterOutcome([render_link_email(ctx.templates, s.app_name, user.email, link, "signup")])


def resend_verification(db: Session, ctx: KitContext, email: str) -> EmailMessage | None:
    """Mail à envoyer, ou None (compte inconnu, déjà vérifié, ou mail trop récent)."""
    user = get_user_by_email(db, email)
    if not user or user.is_verified:
        return None
    if sent_recently(db, user, "signup", ctx.settings.link_email_cooldown_seconds):
        return None
    link = create_link(db, ctx, user, "signup")
    logger.info("Email de vérification renvoyé à %s", user.username)
    return render_link_email(ctx.templates, ctx.settings.app_name, user.email, link, "signup")
