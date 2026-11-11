from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, StringConstraints, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError

from app.core.password_policy import password_problem, username_problem


def _normalize_email(value: str) -> str:
    # Une seule forme en base : évite les doublons "A@x.com" / "a@x.com"
    return value.strip().lower() if isinstance(value, str) else value


# Nom complet : espaces retirés, 100 caractères max
FullName = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100)]


# --- Token ---

class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyRequest(BaseModel):
    token: str

class ClaimRequest(BaseModel):
    attempt_id: str

class ResendRequest(BaseModel):
    email: EmailStr

    _normalize = field_validator("email", mode="before")(_normalize_email)


# --- Mot de passe oublié ---

class ForgotPasswordRequest(ResendRequest):
    pass


class PasswordReset(BaseModel):
    token: str
    new_password: str   # règles vérifiées dans la route (dépend du username / email du compte)


# --- User ---

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


class UserUpdate(BaseModel):
    full_name: FullName | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str   # règles vérifiées dans la route (dépend du username / email du compte)


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    disabled: bool
    role_id: int  # Ajout du champ role_id pour inclure le rôle de l'utilisateur dans la réponse
    is_verified: bool  # Ajout du champ is_verified pour indiquer si l'utilisateur a vérifié son email

    model_config = {"from_attributes": True}  # replaces orm_mode en Pydantic v2


class UserMe(BaseModel):
    id: int
    username: str
    email: EmailStr
    full_name: str | None = None
    is_verified: bool
    role: str
    permissions: list[str]

    model_config = ConfigDict(from_attributes=True)

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
