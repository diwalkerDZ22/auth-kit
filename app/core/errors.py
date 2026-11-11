"""Format d'erreur unique de l'API : {"code": ..., "message": ...}.

Le catalogue ERRORS est la référence pour le frontend (voir Sprint3-Format-erreurs.md).
Dans les routes : raise ApiError("code").
"""
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# code -> (statut HTTP, message affichable)
ERRORS: dict[str, tuple[int, str]] = {
    # Génériques (gestionnaires globaux)
    "validation_error": (422, "Certaines données sont invalides."),
    "rate_limited": (429, "Trop de requêtes, réessayez dans quelques minutes."),
    "not_authenticated": (401, "Authentification requise."),
    "forbidden": (403, "Accès refusé."),
    "not_found": (404, "Ressource introuvable."),
    "method_not_allowed": (405, "Méthode non autorisée."),
    "http_error": (400, "Requête invalide."),
    "internal_error": (500, "Erreur interne, réessayez plus tard."),
    # Routes protégées
    "invalid_token": (401, "Session invalide ou expirée, reconnectez-vous."),
    "account_disabled": (403, "Compte désactivé."),
    "email_not_verified": (403, "Vérifiez votre email avant de vous connecter."),
    "permission_denied": (403, "Vous n'avez pas la permission d'effectuer cette action."),
    # Login
    "invalid_credentials": (401, "Identifiant ou mot de passe incorrect."),
    "login_email_cooldown": (429, "Un email vient d'être envoyé, patientez un instant."),
    "invalid_refresh_token": (401, "Session expirée, reconnectez-vous."),
    "account_not_allowed": (403, "Compte non vérifié ou désactivé."),
    "login_attempt_unknown": (410, "Tentative de connexion inconnue ou déjà utilisée."),
    "login_link_expired": (410, "Lien expiré, recommencez la connexion."),
    "login_approval_expired": (410, "Approbation expirée, recommencez la connexion."),
    # Register / verify
    "username_taken": (409, "Ce nom d'utilisateur est déjà utilisé."),
    "email_taken": (409, "Cette adresse email est déjà utilisée."),
    "account_exists": (409, "Nom d'utilisateur ou email déjà utilisé."),
    "invalid_link": (400, "Lien invalide ou expiré."),
}

# Codes renvoyés pour les HTTPException levées par les librairies (FastAPI, Starlette)
_STATUS_CODES = {
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
}

# Traduction des erreurs Pydantic les plus courantes
_VALIDATION_MESSAGES = {
    "missing": "Champ obligatoire.",
    "string_type": "Doit être une chaîne de caractères.",
    "int_parsing": "Doit être un nombre entier.",
    "int_type": "Doit être un nombre entier.",
    "bool_parsing": "Doit être vrai ou faux.",
    "json_invalid": "JSON invalide.",
    "string_too_short": "Trop court.",
    "string_too_long": "Trop long.",
}


class ApiError(Exception):
    """Erreur métier : le statut et le message viennent du catalogue ERRORS."""

    def __init__(self, code: str, message: str | None = None, headers: dict | None = None, **extra):
        status, default_message = ERRORS[code]
        self.status_code = status
        self.code = code
        self.message = message or default_message
        self.headers = headers
        self.extra = extra
        super().__init__(code)


def error_response(status: int, code: str, message: str, headers: dict | None = None, **extra) -> JSONResponse:
    return JSONResponse(status_code=status, content={"code": code, "message": message, **extra}, headers=headers)


def _field_name(loc: tuple) -> str:
    # ("body", "email") -> "email" ; ("body",) -> "body"
    parts = [str(p) for p in loc]
    if len(parts) > 1 and parts[0] in {"body", "query", "path", "header", "cookie"}:
        parts = parts[1:]
    return ".".join(parts)


def _validation_message(err: dict) -> str:
    if err.get("type") in _VALIDATION_MESSAGES:
        return _VALIDATION_MESSAGES[err["type"]]
    if "email" in str(err.get("msg", "")).lower():
        return "Adresse email invalide."
    return "Valeur invalide."


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return error_response(exc.status_code, exc.code, exc.message, exc.headers, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        return error_response(exc.status_code, code, ERRORS[code][1], getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        fields: dict[str, str] = {}
        for err in exc.errors():
            fields.setdefault(_field_name(err.get("loc", ())), _validation_message(err))
        status, message = ERRORS["validation_error"]
        return error_response(status, "validation_error", message, fields=fields)

    @app.exception_handler(RateLimitExceeded)
    async def _rate_limited(request: Request, exc: RateLimitExceeded):
        logger.warning("Rate-limit dépassé sur %s (%s)", request.url.path, exc.detail)
        status, message = ERRORS["rate_limited"]
        return error_response(status, "rate_limited", message)

    @app.exception_handler(Exception)
    async def _internal_error(request: Request, exc: Exception):
        logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        status, message = ERRORS["internal_error"]
        return error_response(status, "internal_error", message)
