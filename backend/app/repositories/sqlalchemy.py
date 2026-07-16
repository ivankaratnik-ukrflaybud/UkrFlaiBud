from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, TypeVar, cast
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")


class SQLAlchemyRepository[ModelT]:
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def create(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> ModelT | None:
        model = cast(Any, self.model)
        statement = self._exclude_deleted(select(self.model), include_deleted).where(
            model.id == entity_id
        )
        return cast(ModelT | None, await self.session.scalar(statement))

    async def update(self, entity: ModelT) -> ModelT:
        if hasattr(entity, "version"):
            entity.version += 1
        await self.session.flush()
        return entity

    async def soft_delete(self, entity_id: UUID, *, actor_id: UUID | None = None) -> None:
        entity = await self.get(entity_id)
        if entity is None:
            return

        deleted_at = datetime.now(UTC)
        if hasattr(entity, "deleted_at"):
            entity.deleted_at = deleted_at
        if hasattr(entity, "deleted_by"):
            entity.deleted_by = actor_id
        if hasattr(entity, "updated_at"):
            entity.updated_at = deleted_at
        if hasattr(entity, "updated_by"):
            entity.updated_by = actor_id
        if hasattr(entity, "version"):
            entity.version += 1
        await self.session.flush()

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[ModelT]:
        model = cast(Any, self.model)
        statement = (
            self._exclude_deleted(select(self.model), include_deleted)
            .order_by(model.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def refresh(self, entity: ModelT, attribute_names: Sequence[str] | None = None) -> None:
        await self.session.refresh(entity, attribute_names=attribute_names)

    async def flush(self) -> None:
        await self.session.flush()

    def _exclude_deleted(self, statement: Select[tuple[ModelT]], include_deleted: bool) -> Any:
        model = cast(Any, self.model)
        if include_deleted or not hasattr(model, "deleted_at"):
            return statement
        return statement.where(model.deleted_at.is_(None))
