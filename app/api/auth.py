from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.crud.user import get_user_by_username, revoke_refresh_token
from app.db.base import get_db
from app.schemas.user import UserMe, UserOut
from app.db.models import User


router = APIRouter()
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(credentials.credentials)
    # Refuse les refresh tokens (et tout autre token) utilisés comme access token
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    username = payload.get("sub")
    if username is None:
        raise credentials_exception

    user = get_user_by_username(db, username)
    if user is None:
        raise credentials_exception
    return user


def get_current_active_user(user: User = Depends(get_current_user)):
    if user.disabled:
        raise HTTPException(status_code=403, detail="Compte désactivé")
    if not user.is_verified:
        raise HTTPException(status_code=403, detail="Email non vérifié")
    return user

def require_permission(permission: str):
    def dependency(user: User = Depends(get_current_active_user)):
        if permission not in {p.code for p in user.role.permissions}:
            raise HTTPException(status_code=403, detail="Permission refusée")
        return user
    return dependency
    

@router.post("/logout")
def logout(
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    revoke_refresh_token(db, current_user.id)
    print(f"User {current_user.username} logged out successfully.")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserMe)
def me(user: User = Depends(get_current_active_user)):
    return UserMe(
        id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_verified=user.is_verified,
        role=user.role.name,
        permissions=sorted(p.code for p in user.role.permissions),
    )