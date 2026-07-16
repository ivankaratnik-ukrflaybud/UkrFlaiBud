from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(UTC)


class DomainError(Exception):
    code = "domain_error"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundError(DomainError):
    code = "entity_not_found"


class ConflictError(DomainError):
    code = "conflict"


class ValidationError(DomainError):
    code = "validation_error"


class PermissionDeniedError(DomainError):
    code = "permission_denied"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_type: str
    aggregate_id: UUID
    aggregate_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class BaseEntity:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    created_by: UUID | None = None
    updated_by: UUID | None = None
    deleted_at: datetime | None = None
    deleted_by: UUID | None = None
    version: int = 1

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def touch(self, actor_id: UUID | None = None) -> None:
        self.updated_at = utc_now()
        self.updated_by = actor_id
        self.version += 1

    def soft_delete(self, actor_id: UUID | None = None) -> None:
        if self.is_deleted:
            return

        deleted_at = utc_now()
        self.deleted_at = deleted_at
        self.deleted_by = actor_id
        self.updated_at = deleted_at
        self.updated_by = actor_id
        self.version += 1

    def ensure_version(self, expected_version: int) -> None:
        if self.version != expected_version:
            raise ConflictError(
                "Entity version conflict.",
                details={"expected_version": expected_version, "current_version": self.version},
            )
