from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.models.base import BaseEntity, ValidationError

WEAK_PASSWORDS = {
    "1234567890",
    "password123",
    "qwerty12345",
    "admin12345",
    "пароль12345",
}


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def validate_password_strength(password: str) -> None:
    if len(password) < 10:
        raise ValidationError("Password is too short.", {"field": "password"})
    if password.casefold() in WEAK_PASSWORDS:
        raise ValidationError("Password is too weak.", {"field": "password"})
    if not any(character.isalpha() for character in password):
        raise ValidationError("Password must contain a letter.", {"field": "password"})
    if not any(character.isdigit() for character in password):
        raise ValidationError("Password must contain a number.", {"field": "password"})


@dataclass(slots=True)
class User(BaseEntity):
    employee_id: UUID | None = None
    email: str = ""
    normalized_email: str = ""
    password_hash: str = ""
    display_name: str = ""
    is_active: bool = True
    is_superuser: bool = False
    must_change_password: bool = False
    last_login_at: datetime | None = None
    failed_login_attempts: int = 0
    locked_until: datetime | None = None


@dataclass(slots=True)
class Role(BaseEntity):
    name: str = ""
    code: str = ""
    description: str | None = None
    is_system: bool = False
    is_active: bool = True


@dataclass(slots=True)
class Permission:
    id: UUID
    code: str
    name: str
    module: str
    description: str | None = None
    is_active: bool = True


@dataclass(slots=True)
class UserSession:
    id: UUID
    user_id: UUID
    refresh_token_hash: str
    expires_at: datetime
    created_at: datetime
    last_used_at: datetime
    device_name: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    revoked_at: datetime | None = None
    revoke_reason: str | None = None
