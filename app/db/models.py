from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
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