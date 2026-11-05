from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./auth.db"
    SECRET_KEY: str = "dev-only-change-this-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    RESEND_API_KEY: str = ""
    MAIL_FROM: str = "onboarding@resend.dev"
    MAIL_FROM_NAME: str = "FakeJob Auth"
    SIGNUP_TOKEN_EXPIRE_HOURS: int = 24
    LOGIN_TOKEN_EXPIRE_MINUTES: int = 15
    LOGIN_EMAIL_REQUIRED: bool = True
    FRONTEND_VERIFY_URL: str = "http://localhost:5173/verify-email"

    class Config:
        env_file = ".env"


settings = Settings()