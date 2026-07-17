from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    id: UUID
    employee_id: UUID | None
    email: str
    display_name: str
    is_active: bool
    is_superuser: bool
    must_change_password: bool
    last_login_at: datetime | None
    failed_login_attempts: int
    locked_until: datetime | None
    version: int

    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    employee_id: UUID | None = None
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=255)
    temporary_password: str | None = Field(default=None, min_length=10)
    is_active: bool = True
    is_superuser: bool = False
    role_ids: list[UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    version: int = Field(ge=1)
    employee_id: UUID | None = None
    email: EmailStr | None = None
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    is_superuser: bool | None = None


class CreatedUserResponse(BaseModel):
    user: UserResponse
    temporary_password: str | None = None


class RoleResponse(BaseModel):
    id: UUID
    name: str
    code: str
    description: str | None
    is_system: bool
    is_active: bool
    version: int

    model_config = ConfigDict(from_attributes=True)


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    code: str = Field(min_length=1, max_length=80)
    description: str | None = None
    is_active: bool = True


class RoleUpdate(BaseModel):
    version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    is_active: bool | None = None


class PermissionResponse(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    module: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class RoleAssignmentRequest(BaseModel):
    role_ids: list[UUID]


class PermissionAssignmentRequest(BaseModel):
    permission_ids: list[UUID]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class SessionResponse(BaseModel):
    id: UUID
    device_name: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    revoke_reason: str | None

    model_config = ConfigDict(from_attributes=True)


class PasswordResetResponse(BaseModel):
    temporary_password: str
