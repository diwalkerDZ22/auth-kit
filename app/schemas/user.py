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

# --- User ---

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str | None = None
    disabled: bool

    model_config = {"from_attributes": True}  # replaces orm_mode en Pydantic v2