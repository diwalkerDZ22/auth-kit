from pydantic import BaseModel


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
