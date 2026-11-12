"""AuthKit : assemble configuration, adaptateurs, services et routers.

    kit = AuthKit(settings=AuthSettings(), get_db=get_db, email=ResendEmailSender(...))
    kit.install(app)                       # routes /auth/* et /admin/*, gestion des erreurs
    Depends(kit.current_user)              # utilisateur connecté (actif et vérifié)
    Depends(kit.require_permission("jobs:read"))
"""
import logging
from collections.abc import Callable, Iterable

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import Session

from auth_kit.config import AuthSettings
from auth_kit.context import DEFAULT_PERMISSIONS, DEFAULT_ROLES, KitContext, RoleSpec
from auth_kit.errors import ErrorCatalogue, install_error_handlers
from auth_kit.http.deps import make_dependencies
from auth_kit.http.routers.account import build_account_router
from auth_kit.http.routers.admin import build_admin_router
from auth_kit.http.routers.config import build_config_router
from auth_kit.http.routers.login import build_login_router
from auth_kit.http.routers.password import build_password_router
from auth_kit.http.routers.register import build_register_router
from auth_kit.http.routers.sessions import build_devices_router, build_session_router
from auth_kit.ports import BreachChecker, EmailSender, RateLimiter
from auth_kit.services import maintenance, roles as roles_service
from auth_kit.templates import EmailTemplates

logger = logging.getLogger(__name__)

# Toujours actifs : connexion, refresh / logout, /me, changement de mot de passe, /config
FEATURES = frozenset({"register", "password_reset", "devices", "admin"})


class AuthKit:
    def __init__(
        self,
        *,
        settings: AuthSettings,
        get_db: Callable[..., Session],
        email: EmailSender,
        rate_limiter: RateLimiter | None = None,
        breach_checker: BreachChecker | None = None,
        templates: EmailTemplates | None = None,
        features: Iterable[str] = FEATURES,
        permissions: dict[str, str] | None = None,
        roles: dict[str, RoleSpec] | None = None,
        errors: dict[str, tuple[int, str]] | None = None,
        validation_messages: dict[str, str] | None = None,
    ):
        """
        get_db : dépendance FastAPI du projet qui fournit une session SQLAlchemy.
        email : EmailSender (ResendEmailSender, ConsoleEmailSender, ou le vôtre).
        rate_limiter : LimitsRateLimiter("memory://") par défaut ; Redis avec plusieurs workers.
        breach_checker : HibpBreachChecker() pour refuser les mots de passe fuités ; None : désactivé.
        features : sous-ensemble de FEATURES à exposer.
        permissions / roles : remplacent ceux du kit (garder "users:manage" pour l'admin).
        errors : codes ajoutés ou messages remplacés dans le catalogue d'erreurs.
        """
        from auth_kit.adapters.ratelimit import LimitsRateLimiter

        self.features = frozenset(features)
        unknown = self.features - FEATURES
        if unknown:
            raise ValueError(f"Fonctionnalités inconnues : {sorted(unknown)} (disponibles : {sorted(FEATURES)})")

        self.ctx = KitContext(
            settings=settings,
            email=email,
            limiter=rate_limiter if rate_limiter is not None else LimitsRateLimiter("memory://"),
            templates=templates or EmailTemplates(),
            breach_checker=breach_checker,
            permissions=dict(permissions if permissions is not None else DEFAULT_PERMISSIONS),
            roles=dict(roles if roles is not None else DEFAULT_ROLES),
        )
        self.errors = ErrorCatalogue(errors, validation_messages)
        self.deps = make_dependencies(self.ctx, get_db)

        self.auth_router = APIRouter()
        self.auth_router.include_router(build_login_router(self.ctx, self.deps))
        self.auth_router.include_router(build_session_router(self.ctx, self.deps))
        self.auth_router.include_router(build_account_router(self.ctx, self.deps))
        self.auth_router.include_router(build_config_router(self.ctx, self.features))
        if "register" in self.features:
            self.auth_router.include_router(build_register_router(self.ctx, self.deps))
        if "password_reset" in self.features:
            self.auth_router.include_router(build_password_router(self.ctx, self.deps))
        if "devices" in self.features:
            self.auth_router.include_router(build_devices_router(self.ctx, self.deps))
        self.admin_router = build_admin_router(self.ctx, self.deps) if "admin" in self.features else None

    # --- Intégration dans l'application --------------------------------------------------------

    def install(
        self,
        app: FastAPI,
        *,
        auth_prefix: str = "/auth",
        admin_prefix: str = "/admin",
        error_scope: str = "kit",
    ) -> None:
        """Monte les routes et les gestionnaires d'erreurs.

        error_scope : "kit" (défaut) n'applique le format d'erreur du kit qu'à ses propres routes ;
        "app" l'applique à toute l'application ; "none" n'installe aucun gestionnaire (le projet
        appelle alors install_error_handlers lui-même).
        """
        if error_scope not in {"kit", "app", "none"}:
            raise ValueError('error_scope doit valoir "kit", "app" ou "none"')
        if error_scope != "none":
            prefixes = (auth_prefix, admin_prefix) if error_scope == "kit" else None
            install_error_handlers(app, self.errors, prefixes)
        app.include_router(self.auth_router, prefix=auth_prefix)
        if self.admin_router is not None:
            app.include_router(self.admin_router, prefix=admin_prefix)

    # --- Dépendances pour les routes du projet -------------------------------------------------

    @property
    def current_user(self) -> Callable:
        """Utilisateur connecté, actif et vérifié."""
        return self.deps.current_active_user

    def require_permission(self, permission: str) -> Callable:
        return self.deps.require_permission(permission)

    def rate_limit(self, limit: str, name: str | None = None) -> Callable:
        """Limite par IP pour une route du projet : Depends(kit.rate_limit("20/minute"))."""
        return self.deps.rate_limit(name or f"custom:{limit}", limit)

    # --- Tâches -------------------------------------------------------------------------------

    def seed_roles(self, db: Session) -> None:
        roles_service.seed_roles(db, self.ctx.roles, self.ctx.permissions)

    def cleanup(self, db: Session, keep_days: int = 7) -> tuple[int, int]:
        return maintenance.cleanup(db, keep_days)
