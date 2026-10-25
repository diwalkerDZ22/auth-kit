from fastapi import FastAPI
from app.db.base import Base, engine
from app.db.models import User  # noqa: F401 — nécessaire pour que SQLAlchemy détecte le modèle
from app.api.auth import router as auth_router

# Crée les tables si elles n'existent pas encore
Base.metadata.create_all(bind=engine)

app = FastAPI(title="JWT Auth FastApi")

app.include_router(auth_router, prefix="/auth", tags=["auth"])