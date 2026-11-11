"""Administration des utilisateurs (permission users:manage)."""
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.auth import require_permission
from app.core.errors import ApiError
from app.crud.user import bump_token_version, count_active_admins, is_admin_role, list_users
from app.db.base import get_db
from app.db.models import Role, User
from app.schemas.admin import AdminUserList, AdminUserOut, AdminUserUpdate, RoleOut

router = APIRouter(prefix="/admin")
logger = logging.getLogger(__name__)

_admin = require_permission("users:manage")


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise ApiError("user_not_found")
    return user


@router.get("/users", response_model=AdminUserList)
def admin_list_users(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    users, total = list_users(db, search, limit, offset)
    return AdminUserList(items=[AdminUserOut.from_user(u) for u in users], total=total, limit=limit, offset=offset)


@router.get("/users/{user_id}", response_model=AdminUserOut)
def admin_get_user(user_id: int, admin: User = Depends(_admin), db: Session = Depends(get_db)):
    return AdminUserOut.from_user(_get_user_or_404(db, user_id))


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    admin: User = Depends(_admin),
    db: Session = Depends(get_db),
):
    if user_id == admin.id:
        # Évite de se retirer ses propres droits ou de se bloquer par erreur
        raise ApiError("cannot_modify_self")
    user = _get_user_or_404(db, user_id)

    new_role = user.role
    if payload.role is not None:
        new_role = db.query(Role).filter(Role.name == payload.role).first()
        if new_role is None:
            raise ApiError("role_not_found")
    new_disabled = bool(user.disabled) if payload.disabled is None else payload.disabled

    role_changed = new_role.id != user.role_id
    disabled_changed = new_disabled != bool(user.disabled)
    if not (role_changed or disabled_changed):
        return AdminUserOut.from_user(user)

    # Le compte perd ses droits d'admin : il doit rester au moins un autre admin actif
    loses_admin = is_admin_role(user.role) and not user.disabled and (new_disabled or not is_admin_role(new_role))
    if loses_admin and count_active_admins(db, exclude_user_id=user.id) == 0:
        raise ApiError("last_admin")

    user.role_id = new_role.id
    user.disabled = new_disabled
    bump_token_version(user)   # les nouveaux droits s'appliquent immédiatement
    db.commit()
    db.refresh(user)
    logger.info(
        "Admin %s a modifié %s (rôle=%s, désactivé=%s)",
        admin.username, user.username, user.role.name, user.disabled,
    )
    return AdminUserOut.from_user(user)


@router.get("/roles", response_model=list[RoleOut])
def admin_list_roles(admin: User = Depends(_admin), db: Session = Depends(get_db)):
    roles = db.query(Role).order_by(Role.name).all()
    return [
        RoleOut(name=r.name, description=r.description, permissions=sorted(p.code for p in r.permissions))
        for r in roles
    ]
