from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import Role, User
from app.schemas.user import UserCreate
from app.core.security import get_password_hash, verify_password
DEFAULT_ROLE = "user"

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