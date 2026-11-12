"""Tout ce dont les services ont besoin, assemblé par AuthKit et passé explicitement."""
from dataclasses import dataclass, field

from auth_kit.config import AuthSettings
from auth_kit.ports import BreachChecker, EmailSender, RateLimiter
from auth_kit.templates import EmailTemplates

ADMIN_PERMISSION = "users:manage"
DEFAULT_ROLE = "user"


@dataclass(frozen=True)
class RoleSpec:
    description: str
    permissions: tuple[str, ...] = ()


DEFAULT_PERMISSIONS: dict[str, str] = {ADMIN_PERMISSION: "Gérer les utilisateurs et leurs rôles"}
DEFAULT_ROLES: dict[str, RoleSpec] = {
    DEFAULT_ROLE: RoleSpec("Utilisateur standard"),
    "admin": RoleSpec("Administrateur", (ADMIN_PERMISSION,)),
}


@dataclass
class KitContext:
    settings: AuthSettings
    email: EmailSender
    limiter: RateLimiter
    templates: EmailTemplates
    breach_checker: BreachChecker | None = None
    permissions: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PERMISSIONS))
    roles: dict[str, RoleSpec] = field(default_factory=lambda: dict(DEFAULT_ROLES))
