"""Administration des utilisateurs (permission users:manage)."""
import logging

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from auth_kit.context import ADMIN_PERMISSION
from auth_kit.errors import ApiError
from auth_kit.models import Permission, Role, RolePermission, User
from auth_kit.services.accounts import revoke_all_sessions

logger = logging.getLogger(__name__)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def list_users(db: Session, search: str | None, limit: int, offset: int) -> tuple[list[User], int]:
    query = db.query(User)
    if search and search.strip():
        # % et _ tapés par l'admin sont cherchés tels quels, pas comme jokers
        pattern = f"%{_escape_like(search.strip().lower())}%"
        query = query.filter(or_(
            func.lower(User.username).like(pattern, escape="\\"),
            func.lower(User.email).like(pattern, escape="\\"),
        ))
    total = query.count()
    users = query.order_by(User.id).offset(offset).limit(limit).all()
    return users, total


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError("user_not_found")
    return user


def is_admin_role(role: Role) -> bool:
    return any(p.code == ADMIN_PERMISSION for p in role.permissions)


def count_active_admins(db: Session, exclude_user_id: int | None = None, lock: bool = False) -> int:
    """Nombre d'admins actifs.

    lock=True verrouille leurs lignes jusqu'au commit (PostgreSQL) : deux admins qui se
    retirent leurs droits en même temps ne peuvent pas laisser l'application sans admin.
    """
    admin_roles = (
        select(RolePermission.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Permission.code == ADMIN_PERMISSION)
    )
    query = db.query(User.id).filter(User.role_id.in_(admin_roles), User.disabled.isnot(True))
    if lock:
        query = query.with_for_update()
    ids = {row.id for row in query.all()}
    ids.discard(exclude_user_id)
    return len(ids)


def update_user(db: Session, admin: User, user_id: int, role: str | None, disabled: bool | None) -> User:
    if user_id == admin.id:
        # Évite de se retirer ses propres droits ou de se bloquer par erreur
        raise ApiError("cannot_modify_self")
    user = get_user_or_404(db, user_id)

    new_role = user.role
    if role is not None:
        new_role = db.query(Role).filter(Role.name == role).first()
        if new_role is None:
            raise ApiError("role_not_found")
    new_disabled = bool(user.disabled) if disabled is None else disabled

    if new_role.id == user.role_id and new_disabled == bool(user.disabled):
        return user

    # Le compte perd ses droits d'admin : il doit rester au moins un autre admin actif
    loses_admin = is_admin_role(user.role) and not user.disabled and (new_disabled or not is_admin_role(new_role))
    if loses_admin and count_active_admins(db, exclude_user_id=user.id, lock=True) == 0:
        raise ApiError("last_admin")

    user.role_id = new_role.id
    user.disabled = new_disabled
    revoke_all_sessions(user)   # les nouveaux droits s'appliquent immédiatement
    db.commit()
    db.refresh(user)
    logger.info("Admin %s a modifié %s (rôle=%s, désactivé=%s)", admin.username, user.username, user.role.name, user.disabled)
    return user


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.name).all()
