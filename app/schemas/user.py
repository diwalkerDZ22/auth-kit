from pydantic import BaseModel, EmailStr


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

# --- User ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str
    role_id: int  # Ajout du champ role_id pour spécifier le rôle de l'utilisateur lors de la création


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    disabled: bool
    role_id: int  # Ajout du champ role_id pour inclure le rôle de l'utilisateur dans la réponse
    is_verified: bool  # Ajout du champ is_verified pour indiquer si l'utilisateur a vérifié son email

    model_config = {"from_attributes": True}  # replaces orm_mode en Pydantic v2