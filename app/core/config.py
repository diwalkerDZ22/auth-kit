import http

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    resend_api_key: str
    mail_from: str = "onboarding@resend.dev"
    mail_from_name: str = "FakeJob Auth"
    frontend_verify_url: str = "http://127.0.0.1:8000/auth/verify"
    signup_token_expire_hours: int = 24
    login_token_expire_minutes: int = 15
    
    class Config:
        env_file = ".env"


settings = Settings()