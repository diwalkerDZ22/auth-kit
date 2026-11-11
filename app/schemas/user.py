from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


def _normalize_email(value: str) -> str:
    # Une seule forme en base : évite les doublons "A@x.com" / "a@x.com"
    return value.strip().lower()


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
# --- User ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str

    _normalize = field_validator("email", mode="before")(_normalize_email)
  


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