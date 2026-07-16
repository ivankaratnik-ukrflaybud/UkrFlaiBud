from datetime import datetime

import pytest

from app.models.base import BaseEntity, ConflictError


def test_base_entity_generates_uuid_and_timestamps() -> None:
    entity = BaseEntity()

    assert entity.id is not None
    assert isinstance(entity.created_at, datetime)
    assert isinstance(entity.updated_at, datetime)
    assert entity.created_at.tzinfo is not None
    assert entity.version == 1


def test_soft_delete_marks_entity_and_increments_version() -> None:
    entity = BaseEntity()

    entity.soft_delete()

    assert entity.is_deleted
    assert entity.deleted_at is not None
    assert entity.version == 2


def test_optimistic_locking_detects_version_conflict() -> None:
    entity = BaseEntity()

    with pytest.raises(ConflictError):
        entity.ensure_version(2)
