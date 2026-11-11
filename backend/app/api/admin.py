from fastapi import APIRouter, Depends

from app.api.auth import require_permission

router = APIRouter()


@router.get("/admin/users")
def admin_users(user=Depends(require_permission("users:manage"))):
    # Route bouchon : sera remplacée par la vraie liste des utilisateurs
    return {"users": []}