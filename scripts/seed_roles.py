import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models import Role

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def seed_roles() -> None:
    db = SessionLocal()
    try:
        existing = db.query(Role).filter(Role.name.in_(["user", "admin"])).all()
        existing_names = {role.name for role in existing}

        for name, description in [
            ("user", "Utilisateur standard"),
            ("admin", "Administrateur"),
        ]:
            if name not in existing_names:
                db.add(Role(name=name, description=description))

        db.commit()
        print("Rôles ajoutés avec succès.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_roles()
