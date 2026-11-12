"""Création / synchronisation des rôles et permissions, à partir de ce que déclare le projet.

    AuthKit(..., permissions={"jobs:classify": "Classer les offres"},
            roles={"user": RoleSpec("Utilisateur"), "admin": RoleSpec("Admin", ("users:manage", "jobs:classify"))})
    kit.seed_roles(db)

Idempotent. Attention : les permissions de chaque rôle listé sont resynchronisées ; une
permission ajoutée à la main en base à un rôle listé lui est retirée.
"""
import logging

from sqlalchemy.orm import Session

from auth_kit.context import RoleSpec
from auth_kit.models import Permission, Role

logger = logging.getLogger(__name__)


def seed_roles(db: Session, roles: dict[str, RoleSpec], permissions: dict[str, str]) -> None:
    unknown = {code for spec in roles.values() for code in spec.permissions} - permissions.keys()
    if unknown:
        raise ValueError(f"Permissions utilisées par un rôle mais non déclarées : {sorted(unknown)}")

    perms: dict[str, Permission] = {}
    for code, description in permissions.items():
        perm = db.query(Permission).filter(Permission.code == code).first()
        if not perm:
            perm = Permission(code=code, description=description)
            db.add(perm)
        perms[code] = perm
    db.flush()

    for name, spec in roles.items():
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            role = Role(name=name, description=spec.description)
            db.add(role)
            db.flush()
        role.permissions = [perms[code] for code in spec.permissions]

    db.commit()
    logger.info("Rôles synchronisés : %s", ", ".join(f"{n} ({len(s.permissions)})" for n, s in roles.items()))
