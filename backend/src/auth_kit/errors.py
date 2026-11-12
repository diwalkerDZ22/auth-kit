"""Format d'erreur unique : {"code": ..., "message": ...} (+ "fields" pour 422).

    raise ApiError("code")            # dans le kit ou dans les routes du projet

Le catalogue (statut HTTP + message) est propre à chaque AuthKit : un projet ajoute ses
codes ou traduit les messages avec AuthKit(errors={...}). Voir docs/Sprint3-Format-erreurs.md.
"""
import logging
from collections.abc import Iterable

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# code -> (statut HTTP, message affichable)
DEFAULT_ERRORS: dict[str, tuple[int, str]] = {
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
    "csrf_missing": (403, "Requête refusée : en-tête de protection CSRF manquant."),
    "account_not_allowed": (403, "Compte non vérifié ou désactivé."),
    "login_attempt_unknown": (410, "Tentative de connexion inconnue ou déjà utilisée."),
    "login_link_expired": (410, "Lien expiré, recommencez la connexion."),
    "login_approval_expired": (410, "Approbation expirée, recommencez la connexion."),
    # Register / verify
    "username_taken": (409, "Ce nom d'utilisateur est déjà utilisé."),
    "account_exists": (409, "Nom d'utilisateur ou email déjà utilisé."),
    "invalid_link": (400, "Lien invalide ou expiré."),
    # Sessions (appareils connectés)
    "session_not_found": (404, "Session introuvable ou déjà fermée."),
    # Profil / mot de passe
    "invalid_current_password": (400, "Mot de passe actuel incorrect."),
    "email_unavailable": (503, "Impossible d'envoyer l'email pour le moment, réessayez plus tard."),
    # Administration
    "user_not_found": (404, "Utilisateur introuvable."),
    "role_not_found": (400, "Rôle inconnu."),
    "cannot_modify_self": (400, "Vous ne pouvez pas modifier votre propre compte depuis l'administration."),
    "last_admin": (409, "Impossible : ce compte est le dernier administrateur actif."),
}

# Traduction des erreurs Pydantic les plus courantes
DEFAULT_VALIDATION_MESSAGES: dict[str, str] = {
    "missing": "Champ obligatoire.",
    "string_type": "Doit être une chaîne de caractères.",
    "int_parsing": "Doit être un nombre entier.",
    "int_type": "Doit être un nombre entier.",
    "bool_parsing": "Doit être vrai ou faux.",
    "json_invalid": "JSON invalide.",
    "string_too_short": "Trop court.",
    "string_too_long": "Trop long.",
    "greater_than_equal": "Valeur trop petite.",
    "less_than_equal": "Valeur trop grande.",
    "url_parsing": "URL invalide.",
    "value_error.email": "Adresse email invalide.",
    "default": "Valeur invalide.",
}

# Codes renvoyés pour les HTTPException levées par les librairies (FastAPI, Starlette)
_STATUS_CODES = {401: "not_authenticated", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}


class ApiError(Exception):
    """Erreur métier. Le statut et le message viennent du catalogue au moment de la réponse."""

    def __init__(self, code: str, message: str | None = None, headers: dict | None = None, **extra):
        self.code = code
        self.message = message
        self.headers = headers
        self.extra = extra
        super().__init__(code)


class ErrorCatalogue:
    def __init__(
        self,
        errors: dict[str, tuple[int, str]] | None = None,
        validation_messages: dict[str, str] | None = None,
    ):
        self.errors = {**DEFAULT_ERRORS, **(errors or {})}
        self.validation_messages = {**DEFAULT_VALIDATION_MESSAGES, **(validation_messages or {})}

    def add(self, errors: dict[str, tuple[int, str]]) -> None:
        self.errors.update(errors)

    def resolve(self, code: str) -> tuple[int, str]:
        if code not in self.errors:
            logger.error("Code d'erreur absent du catalogue : %s", code)
            return self.errors["internal_error"]
        return self.errors[code]

    def response(self, code: str, message: str | None = None, headers: dict | None = None, **extra) -> JSONResponse:
        status, default_message = self.resolve(code)
        if code not in self.errors:   # code inconnu : déjà loggé par resolve()
            code, message = "internal_error", None
        return JSONResponse(
            status_code=status,
            content={"code": code, "message": message or default_message, **extra},
            headers=headers,
        )

    def validation_message(self, err: dict) -> str:
        # Validateurs du kit (PydanticCustomError("kit_...", message)) : message déjà rédigé
        error_type = str(err.get("type", ""))
        if error_type.startswith("kit_"):
            return err["msg"]
        if error_type in self.validation_messages:
            return self.validation_messages[error_type]
        if "email" in str(err.get("msg", "")).lower():
            return self.validation_messages["value_error.email"]
        return self.validation_messages["default"]


def _field_name(loc: tuple) -> str:
    # ("body", "email") -> "email" ; ("body",) -> "body"
    parts = [str(p) for p in loc]
    if len(parts) > 1 and parts[0] in {"body", "query", "path", "header", "cookie"}:
        parts = parts[1:]
    return ".".join(parts)


def install_error_handlers(app: FastAPI, catalogue: ErrorCatalogue, prefixes: Iterable[str] | None = None) -> None:
    """Gestionnaires d'erreurs au format du kit.

    prefixes : chemins concernés par le format du kit pour les erreurs génériques (404, 422, 500…).
    None : toute l'application. Les autres routes gardent le comportement par défaut de FastAPI.
    ApiError est toujours rendue au format du kit, d'où qu'elle vienne.
    """
    scoped = tuple(prefixes) if prefixes is not None else None

    def in_scope(request: Request) -> bool:
        return scoped is None or request.url.path.startswith(scoped)

    @app.exception_handler(ApiError)
    async def _api_error(request: Request, exc: ApiError):
        return catalogue.response(exc.code, exc.message, exc.headers, **exc.extra)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        if not in_scope(request):
            return await http_exception_handler(request, exc)
        code = _STATUS_CODES.get(exc.status_code, "http_error")
        status, message = catalogue.resolve(code)
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": message},
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        if not in_scope(request):
            return await request_validation_exception_handler(request, exc)
        fields: dict[str, str] = {}
        for err in exc.errors():
            fields.setdefault(_field_name(err.get("loc", ())), catalogue.validation_message(err))
        return catalogue.response("validation_error", fields=fields)

    @app.exception_handler(Exception)
    async def _internal_error(request: Request, exc: Exception):
        logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
        if not in_scope(request):
            return PlainTextResponse("Internal Server Error", status_code=500)
        return catalogue.response("internal_error")
