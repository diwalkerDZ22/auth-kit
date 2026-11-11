from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Obligatoires : pas de valeur par défaut, l'app refuse de démarrer sans elles
    DATABASE_URL: str
    # Signe tous les JWT : au moins 32 caractères (python -c "import secrets; print(secrets.token_hex(32))")
    SECRET_KEY: str = Field(min_length=32)
    RESEND_API_KEY: str

    # Nom affiché (titre de l'API, expéditeur des mails)
    APP_NAME: str = "auth-kit"

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # "console" (dev uniquement) : les mails sont écrits dans les logs au lieu d'être envoyés
    EMAIL_BACKEND: Literal["resend", "console"] = "resend"
    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str | None = None   # par défaut : APP_NAME
    SIGNUP_TOKEN_EXPIRE_HOURS: int = 24
    LOGIN_TOKEN_EXPIRE_MINUTES: int = 15
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    LOGIN_EMAIL_REQUIRED: bool = True   # sûr par défaut ; false seulement dans ton .env de dev
    FRONTEND_VERIFY_URL: str = "http://localhost:5173/verify-email"
    FRONTEND_RESET_URL: str = "http://localhost:5173/reset-password"
    # Origines autorisées par CORS ; dans .env au format JSON : ["http://a","http://b"]
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]
    LOG_LEVEL: str = "INFO"

    # Cookie httpOnly du refresh token (Sprint 6)
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_PATH: str = "/"
    COOKIE_SECURE: bool = True          # false seulement en dev HTTP
    COOKIE_SAMESITE: Literal["strict", "lax", "none"] = "strict"   # "none" exige COOKIE_SECURE=true

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def mail_sender_name(self) -> str:
        return self.MAIL_FROM_NAME or self.APP_NAME


settings = Settings()
