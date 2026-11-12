"""Application de démonstration : montre comment un projet intègre auth-kit.

    cd backend
    python -m uvicorn --factory example.main:create_app --reload

Tout ce qui est ici appartient au projet (base, CORS, logs, choix des adaptateurs) ;
le kit ne lit que ses réglages AUTH_*.
"""
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.orm import sessionmaker

from auth_kit import CSRF_HEADER, AuthKit, AuthSettings
from auth_kit.adapters import ConsoleEmailSender, HibpBreachChecker, LimitsRateLimiter, ResendEmailSender
from auth_kit.db import create_engine_from_url, session_dependency
from auth_kit.models import User


class AppSettings(BaseSettings):
    """Réglages du projet (sans préfixe). Ceux du kit sont lus par AuthSettings (préfixe AUTH_)."""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    DATABASE_SSLMODE: str | None = "require"
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    LOG_LEVEL: str = "INFO"
    # "console" (dev uniquement) : les mails sont écrits dans les logs au lieu d'être envoyés
    EMAIL_BACKEND: str = "resend"
    RESEND_API_KEY: str = ""
    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str = "auth-kit"
    # "redis://host:6379" avec plusieurs workers ou serveurs
    RATE_LIMIT_STORAGE_URI: str = "memory://"
    PASSWORD_BREACH_CHECK: bool = True


def _configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    for name in ("auth_kit", "example"):
        logger = logging.getLogger(name)
        logger.setLevel(level.upper())
        if not logger.handlers:
            logger.addHandler(handler)


def create_app(env_file: str | None = ".env") -> FastAPI:
    app_settings = AppSettings(_env_file=env_file)
    auth_settings = AuthSettings(_env_file=env_file)
    _configure_logging(app_settings.LOG_LEVEL)

    engine = create_engine_from_url(app_settings.DATABASE_URL, sslmode=app_settings.DATABASE_SSLMODE)
    get_db = session_dependency(sessionmaker(bind=engine, autoflush=False))

    if app_settings.EMAIL_BACKEND == "console":
        email = ConsoleEmailSender()
    else:
        email = ResendEmailSender(
            app_settings.RESEND_API_KEY,
            f"{app_settings.MAIL_FROM_NAME} <{app_settings.MAIL_FROM}>",
        )

    kit = AuthKit(
        settings=auth_settings,
        get_db=get_db,
        email=email,
        rate_limiter=LimitsRateLimiter(app_settings.RATE_LIMIT_STORAGE_URI),
        breach_checker=HibpBreachChecker() if app_settings.PASSWORD_BREACH_CHECK else None,
    )

    app = FastAPI(title=auth_settings.app_name)
    # Frontend sur une autre origine que l'API : son origine dans CORS_ORIGINS, et le header CSRF
    # autorisé, sinon /auth/refresh et /auth/logout échouent au preflight.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type", CSRF_HEADER],
    )
    kit.install(app)

    # Exemple de route métier protégée
    @app.get("/hello", tags=["exemple"])
    def hello(user: User = Depends(kit.current_user)):
        return {"message": f"Bonjour {user.full_name or user.username} !"}

    app.state.auth_kit = kit
    app.state.engine = engine
    return app
