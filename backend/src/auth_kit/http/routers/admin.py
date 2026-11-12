"""Administration des utilisateurs (fonctionnalité "admin", permission users:manage)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from auth_kit.context import ADMIN_PERMISSION, KitContext
from auth_kit.http.deps import AuthDependencies
from auth_kit.http.schemas import AdminUserList, AdminUserOut, AdminUserUpdate, RoleOut
from auth_kit.models import User
from auth_kit.services import admin as service


def build_admin_router(ctx: KitContext, deps: AuthDependencies) -> APIRouter:
    router = APIRouter(tags=["admin"])
    admin_only = deps.require_permission(ADMIN_PERMISSION)

    @router.get("/users", response_model=AdminUserList)
    def list_users(
        search: str | None = Query(default=None, max_length=100),
        limit: int = Query(default=20, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        admin: User = Depends(admin_only),
        db: Session = Depends(deps.get_db),
    ):
        users, total = service.list_users(db, search, limit, offset)
        return AdminUserList(items=[AdminUserOut.from_user(u) for u in users], total=total, limit=limit, offset=offset)

    @router.get("/users/{user_id}", response_model=AdminUserOut)
    def get_user(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(deps.get_db)):
        return AdminUserOut.from_user(service.get_user_or_404(db, user_id))

    @router.patch("/users/{user_id}", response_model=AdminUserOut)
    def update_user(
        user_id: int,
        payload: AdminUserUpdate,
        admin: User = Depends(admin_only),
        db: Session = Depends(deps.get_db),
    ):
        return AdminUserOut.from_user(service.update_user(db, admin, user_id, payload.role, payload.disabled))

    @router.get("/roles", response_model=list[RoleOut])
    def list_roles(admin: User = Depends(admin_only), db: Session = Depends(deps.get_db)):
        return [
            RoleOut(name=r.name, description=r.description, permissions=sorted(p.code for p in r.permissions))
            for r in service.list_roles(db)
        ]

    return router
