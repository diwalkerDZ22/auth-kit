"""Schémas des requêtes et réponses HTTP (source du contrat OpenAPI, dont les types du frontend sont générés)."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, EmailStr, StringConstraints, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from auth_kit.passwords import password_problem, username_problem


def _normalize_email(value: str) -> str:
    # Une seule forme en base : évite les doublons "A@x.com" / "a@x.com"
    return value.strip().lower() if isinstance(value, str) else value


# Nom complet : espaces retirés, 100 caractères max
FullName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


# --- Réponses génériques ---------------------------------------------------------------------

class MessageOut(BaseModel):
    message: str


# --- Connexion / sessions ----------------------------------------------------------------------

class AccessToken(BaseModel):
    # Le refresh token n'est jamais dans le corps : il part en cookie httpOnly
    access_token: str
    token_type: Literal["bearer"]
    expires_in: int   # secondes


class LoginEmailSent(BaseModel):
    code: Literal["login_email_sent"]
    attempt_id: str
    message: str


class LoginPending(BaseModel):
    code: Literal["login_pending"]
    message: str


class ClaimRequest(BaseModel):
    attempt_id: str


class TokenRequest(BaseModel):
    token: str


class VerifyOut(BaseModel):
    purpose: Literal["signup", "login"]
    message: str


class SessionOut(BaseModel):
    """Un appareil connecté (GET /auth/sessions)."""
    id: str
    created_at: datetime
    last_used_at: datetime
    ip: str | None = None
    user_agent: str | None = None
    current: bool   # session de la requête

    @classmethod
    def from_session(cls, session, current_id: str) -> "SessionOut":
        return cls(
            id=session.id,
            created_at=session.created_at,
            last_used_at=session.last_used_at,
            ip=session.ip,
            user_agent=session.user_agent,
            current=session.id == current_id,
        )


class RevokeOut(MessageOut):
    current: bool


class RevokeOthersOut(MessageOut):
    count: int


# --- Inscription -------------------------------------------------------------------------------

class EmailRequest(BaseModel):
    email: EmailStr

    _normalize = field_validator("email", mode="before")(_normalize_email)


class UserCreate(BaseModel):
    # L'ordre compte : password est validé après username et email (info.data)
    username: str
    email: EmailStr
    full_name: FullName | None = None
    password: str

    _normalize = field_validator("email", mode="before")(_normalize_email)

    @field_validator("username")
    @classmethod
    def _check_username(cls, value: str) -> str:
        problem = username_problem(value)
        if problem:
            raise PydanticCustomError("kit_username", problem)
        return value

    @field_validator("password")
    @classmethod
    def _check_password(cls, value: str, info: ValidationInfo) -> str:
        problem = password_problem(value, info.data.get("username"), info.data.get("email"))
        if problem:
            raise PydanticCustomError("kit_password", problem)
        return value


# --- Compte ------------------------------------------------------------------------------------

class UserUpdate(BaseModel):
    full_name: FullName | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str   # règles vérifiées par le service (dépendent du username / email du compte)


class PasswordReset(BaseModel):
    token: str
    new_password: str


class UserMe(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None
    is_verified: bool
    role: str
    permissions: list[str]

    @classmethod
    def from_user(cls, user) -> "UserMe":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            is_verified=user.is_verified,
            role=user.role.name,
            permissions=sorted(p.code for p in user.role.permissions),
        )


# --- Configuration publique (GET /auth/config) -------------------------------------------------

class PasswordRules(BaseModel):
    min_length: int
    max_bytes: int
    breach_check: bool


class AuthConfigOut(BaseModel):
    """Ce que le frontend doit savoir pour s'adapter, sans recopier les règles du backend."""
    features: list[Literal["register", "password_reset", "devices", "admin"]]
    login_email_required: bool
    access_token_expire_seconds: int
    login_link_expire_seconds: int
    password: PasswordRules
    username_pattern: str


# --- Administration ----------------------------------------------------------------------------

class AdminUserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    role: str
    disabled: bool
    is_verified: bool

    @classmethod
    def from_user(cls, user) -> "AdminUserOut":
        return cls(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            role=user.role.name,
            disabled=bool(user.disabled),
            is_verified=user.is_verified,
        )


class AdminUserList(BaseModel):
    items: list[AdminUserOut]
    total: int
    limit: int
    offset: int


class AdminUserUpdate(BaseModel):
    role: str | None = None
    disabled: bool | None = None


class RoleOut(BaseModel):
    name: str
    description: str | None = None
    permissions: list[str]
