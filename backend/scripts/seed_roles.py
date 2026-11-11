import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Même connexion que l'app (driver PostgreSQL et SSL gérés dans app/db/base.py)
from app.db.base import SessionLocal
from app.db.models import Permission, Role

# Actions atomiques : code -> description
# Un projet qui utilise auth-kit ajoute ici ses propres permissions (ex. "jobs:classify").
PERMISSIONS = {
    "users:manage": "Gérer les utilisateurs et leurs rôles",
}

# nom du rôle -> (description, permissions)
# Attention : le script resynchronise les permissions de chaque rôle listé ici.
ROLES = {
    "user": ("Utilisateur standard", []),
    "admin": ("Administrateur", ["users:manage"]),
}


def seed_roles() -> None:
    db = SessionLocal()
    try:
        # 1. Permissions : créées si absentes
        perms: dict[str, Permission] = {}
        for code, description in PERMISSIONS.items():
            perm = db.query(Permission).filter(Permission.code == code).first()
            if not perm:
                perm = Permission(code=code, description=description)
                db.add(perm)
            perms[code] = perm
        db.flush()

        # 2. Rôles : créés si absents, puis synchronisés avec leur liste de permissions
        for name, (description, codes) in ROLES.items():
            role = db.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(name=name, description=description)
                db.add(role)
                db.flush()

            role.permissions = [perms[code] for code in codes]

        db.commit()
        print("Rôles et permissions synchronisés.")
        for name, (_, codes) in ROLES.items():
            print(f"  {name}: {', '.join(codes)}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()