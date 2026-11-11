from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from app.db.models import Permission, Role, User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
DEFAULT_ROLE = "user"
ADMIN_PERMISSION = "users:manage"

def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> User | None:
    # Insensible à la casse : couvre aussi les comptes créés avant la normalisation
    return db.query(User).filter(func.lower(User.email) == email.strip().lower()).first()


def create_user(db: Session, user_in: UserCreate) -> User:
    role = db.query(Role).filter(Role.name == DEFAULT_ROLE).one()
    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=get_password_hash(user_in.password),
        disabled=False,
        role_id=role.id,
        is_verified=False
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def save_refresh_token(db: Session, user_id: int, token: str):
    db.query(User).filter(User.id == user_id).update({"refresh_token": token})
    db.commit()

def revoke_refresh_token(db: Session, user_id: int):
    db.query(User).filter(User.id == user_id).update({"refresh_token": None})
    db.commit()


def bump_token_version(user: User) -> None:
    """Révoque tous les tokens du compte (access et refresh). Le commit reste à l'appelant."""
    user.token_version = (user.token_version or 0) + 1
    user.refresh_token = None


def set_password(user: User, new_password: str) -> None:
    """Change le mot de passe et révoque les sessions. Le commit reste à l'appelant."""
    user.hashed_password = get_password_hash(new_password)
    bump_token_version(user)


def list_users(db: Session, search: str | None, limit: int, offset: int) -> tuple[list[User], int]:
    query = db.query(User)
    if search:
        pattern = f"%{search.strip().lower()}%"
        query = query.filter(or_(func.lower(User.username).like(pattern), func.lower(User.email).like(pattern)))
    total = query.count()
    users = query.order_by(User.id).offset(offset).limit(limit).all()
    return users, total


def is_admin_role(role: Role) -> bool:
    return any(p.code == ADMIN_PERMISSION for p in role.permissions)


def count_active_admins(db: Session, exclude_user_id: int | None = None) -> int:
    query = (
        db.query(User)
        .join(User.role)
        .join(Role.permissions)
        .filter(Permission.code == ADMIN_PERMISSION, User.disabled.isnot(True))
    )
    if exclude_user_id is not None:
        query = query.filter(User.id != exclude_user_id)
    return query.distinct().count()
