"""auth-kit : authentification et autorisation pour FastAPI, en bibliothèque.

    from auth_kit import AuthKit, AuthSettings
    from auth_kit.adapters import ResendEmailSender

    kit = AuthKit(settings=AuthSettings(), get_db=get_db, email=ResendEmailSender(api_key, "App <no-reply@app.fr>"))
    kit.install(app)

Voir docs/Bibliotheque.md.
"""
from auth_kit.config import AuthSettings
from auth_kit.context import ADMIN_PERMISSION, RoleSpec
from auth_kit.errors import ApiError, install_error_handlers
from auth_kit.http.cookies import CSRF_HEADER
from auth_kit.kit import FEATURES, AuthKit
from auth_kit.templates import EmailTemplates, LinkEmail

__version__ = "0.8.0"

__all__ = [
    "ADMIN_PERMISSION",
    "CSRF_HEADER",
    "FEATURES",
    "ApiError",
    "AuthKit",
    "AuthSettings",
    "EmailTemplates",
    "LinkEmail",
    "RoleSpec",
    "install_error_handlers",
]
