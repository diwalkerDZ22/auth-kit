from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)
    refresh_token = Column(String, nullable=True)
    
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    role = relationship("Role", back_populates="users",lazy="joined")  # Utilisation de lazy="joined" pour charger le rôle en même temps que l'utilisateur
    
    is_verified = Column(Boolean, default=False, nullable=False)
    email_verifications = relationship(
        "EmailVerification",
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
        CheckConstraint("purpose IN ('signup', 'login')", name="ck_email_verifications_purpose"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    purpose = Column(String(16), nullable=False)
    token_hash = Column(String(64), unique=True, index=True, nullable=False)  # sha256 hex = 64 car.
    attempt_hash = Column(String(64), unique=True, index=True, nullable=True)  # secret de la page de login (None pour signup)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)       # lien consommé (ou remplacé)
    approved_at = Column(DateTime(timezone=True), nullable=True)   # lien login cliqué
    claimed_at = Column(DateTime(timezone=True), nullable=True)    # tokens remis à la page d'origine
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user = relationship("User", back_populates="email_verifications")