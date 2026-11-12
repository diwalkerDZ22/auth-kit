"""Tables du kit.

Le projet peut déclarer ses propres modèles sur la même base, pour une seule metadata
et un seul autogenerate Alembic :

    from auth_kit.models import Base, User

    class Job(Base):
        __tablename__ = "jobs"
        owner_id = Column(ForeignKey("users.id"))

Ou garder sa propre base et référencer l'utilisateur par colonne : ForeignKey(User.id).
"""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import DeclarativeBase, relationship

from auth_kit.sqltypes import UTCDateTime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    # Incrémenté pour révoquer tous les access tokens émis (mot de passe, désactivation, rôle)
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users",lazy="joined")  # Utilisation de lazy="joined" pour charger le rôle en même temps que l'utilisateur
    
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verifications = relationship(
        "EmailVerification",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sessions = relationship(
        "UserSession",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)

    users = relationship("User", back_populates="role")
    permissions = relationship(
        "Permission",
        secondary="role_permissions",
        back_populates="roles",
        lazy="selectin",
    )

class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    roles = relationship(
        "Role",
        secondary="role_permissions",
        back_populates="permissions",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id = Column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class EmailVerification(Base):
    __tablename__ = "email_verifications"
    __table_args__ = (
        CheckConstraint("purpose IN ('signup', 'login', 'reset')", name="ck_email_verifications_purpose"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose = Column(String(16), nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # sha256 hex = 64 car.
    attempt_hash = Column(String(64), unique=True, index=True, nullable=True)  # secret de la page de login (None pour signup)
    expires_at = Column(UTCDateTime(), nullable=False)
    used_at = Column(UTCDateTime(), nullable=True)       # lien consommé (ou remplacé)
    approved_at = Column(UTCDateTime(), nullable=True)   # lien login cliqué
    claimed_at = Column(UTCDateTime(), nullable=True)    # tokens remis à la page d'origine
    created_at = Column(UTCDateTime(), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="email_verifications")


class UserSession(Base):
    """Une session = un appareil / navigateur connecté (voir docs/Sprint7-Sessions-et-durcissement.md).

    Le refresh token (cookie httpOnly) est une valeur aléatoire opaque : seul son SHA-256 est stocké.
    Il est remplacé à chaque refresh ; l'ancien hash est gardé pour le délai de grâce et la
    détection de réutilisation.
    """
    __tablename__ = "user_sessions"

    id = Column(String(32), primary_key=True)   # aléatoire, repris dans le claim "sid" de l'access token
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), unique=True, nullable=False)
    previous_token_hash = Column(String(64), index=True, nullable=True)
    rotated_at = Column(UTCDateTime(), nullable=True)
    user_agent = Column(String(255), nullable=True)
    ip = Column(String(64), nullable=True)
    created_at = Column(UTCDateTime(), nullable=False, server_default=func.now())
    last_used_at = Column(UTCDateTime(), nullable=False, server_default=func.now())
    expires_at = Column(UTCDateTime(), nullable=False)
    revoked_at = Column(UTCDateTime(), nullable=True)

    user = relationship("User", back_populates="sessions")