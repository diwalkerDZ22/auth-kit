"""Réglages du kit. Aucune instance globale : le projet crée la sienne et la passe à AuthKit.

    settings = AuthSettings()                       # variables d'environnement AUTH_*
    settings = AuthSettings(_env_file=".env")       # + fichier .env
    settings = AuthSettings(secret_key="...", cookie_secure=False)   # en code

L'infrastructure (base de données, CORS, envoi d'emails, Redis) n'est pas ici :
elle appartient à l'application qui intègre le kit.
"""
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Limites par IP de chaque route publique (format de la librairie limits)
DEFAULT_RATE_LIMITS: dict[str, str] = {
    "login": "10/15minutes",
    "claim": "60/minute",        # interrogée en boucle par la page de login
    "deny": "10/15minutes",
    "verify": "10/15minutes",
    "refresh": "30/minute",
    "register": "5/15minutes",
    "resend": "3/15minutes",
    "forgot": "3/15minutes",
    "reset": "10/15minutes",
    "change_password": "5/15minutes",
}


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_", extra="ignore")

    # Signe les access tokens : au moins 32 caractères (python -c "import secrets; print(secrets.token_hex(32))")
    secret_key: str = Field(min_length=32)
    algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    # Nom affiché (expéditeur et contenu des mails)
    app_name: str = "auth-kit"

    access_token_expire_minutes: int = 30
    # Durée de vie d'une session sans activité (prolongée à chaque refresh)
    refresh_token_expire_days: int = 7
    # Un refresh token qui vient d'être remplacé reste accepté ce délai (onglets simultanés),
    # sans nouveau cookie. Au-delà, sa réutilisation est traitée comme un vol.
    refresh_reuse_grace_seconds: int = 30

    signup_token_expire_hours: int = 24
    login_token_expire_minutes: int = 15
    reset_token_expire_minutes: int = 30
    # Délai pour récupérer les tokens après le clic sur le lien de connexion
    login_claim_window_minutes: int = 2
    # Connexion en deux étapes (mot de passe + lien email). False : dev uniquement (Swagger)
    login_email_required: bool = True
    # Anti-spam des mails : un mail de login par minute, un mail signup / reset par 2 minutes
    login_email_cooldown_seconds: int = 60
    link_email_cooldown_seconds: int = 120
    account_exists_mail_limit: str = "1/30minutes"

    # Échecs de mot de passe tolérés par compte, toutes IP confondues
    login_failures_per_account: str = "10/15minutes"
    # Limites par IP, fusionnées avec DEFAULT_RATE_LIMITS (dans .env : JSON)
    rate_limits: dict[str, str] = Field(default_factory=dict)

    # Pages du frontend ouvertes par les liens des mails
    frontend_verify_url: str = "http://localhost:5173/verify-email"
    frontend_reset_url: str = "http://localhost:5173/reset-password"
    # Page HTML GET <prefix>/verify pour tester les liens sans frontend (dev uniquement)
    verify_test_page: bool = False

    # Cookie httpOnly du refresh token
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_path: str = "/"
    cookie_secure: bool = True          # false seulement en dev HTTP
    cookie_samesite: Literal["strict", "lax", "none"] = "strict"   # "none" exige cookie_secure=true

    def rate_limit(self, name: str) -> str:
        return {**DEFAULT_RATE_LIMITS, **self.rate_limits}[name]
