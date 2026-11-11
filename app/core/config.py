from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Obligatoires : pas de valeur par défaut, l'app refuse de démarrer sans elles
    DATABASE_URL: str
    SECRET_KEY: str
    RESEND_API_KEY: str

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str = "FakeJob Auth"
    SIGNUP_TOKEN_EXPIRE_HOURS: int = 24
    LOGIN_TOKEN_EXPIRE_MINUTES: int = 15
    LOGIN_EMAIL_REQUIRED: bool = True   # sûr par défaut ; false seulement dans ton .env de dev
    FRONTEND_VERIFY_URL: str = "http://localhost:5173/verify-email"
    # Origines autorisées par CORS ; dans .env au format JSON : ["http://a","http://b"]
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()