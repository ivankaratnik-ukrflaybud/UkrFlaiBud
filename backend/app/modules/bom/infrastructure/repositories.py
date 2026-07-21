from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bom.infrastructure.models import (
    BomAttachmentModel,
    BomLineModel,
    BomSpecificationModel,
    BomVersionModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection

BomModel = BomSpecificationModel | BomVersionModel | BomLineModel | BomAttachmentModel


class BomQueryRepository[ModelT: BomModel]:
    sortable_fields: dict[str, Any] = {}

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model
        self.base_repository = SQLAlchemyRepository(session, model)

    async def create(self, entity: ModelT) -> ModelT:
        return await self.base_repository.create(entity)

    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> ModelT | None:
        return await self.base_repository.get(entity_id, include_deleted=include_deleted)

    async def update(self, entity: ModelT) -> ModelT:
        return await self.base_repository.update(entity)

    async def soft_delete(self, entity_id: UUID) -> None:
        await self.base_repository.soft_delete(entity_id)

    async def exists(self, *conditions: Any) -> bool:
        statement = select(func.count()).select_from(self.model).where(and_(*conditions))
        return bool(await self.session.scalar(statement))

    async def list(
        self,
        *,
        filters: dict[str, object],
        sort_by: str,
        sort_direction: SortDirection,
        limit: int,
        offset: int,
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        statement = self._apply_filters(
            self.base_repository._exclude_deleted(select(self.model), include_deleted),
            filters,
        )
        total = await self.session.scalar(statement.with_only_columns(func.count()).order_by(None))
        sort_column = self.sortable_fields.get(sort_by, self.sortable_fields["created_at"])
        ordered = statement.order_by(
            sort_column.desc() if sort_direction == SortDirection.DESC else sort_column.asc()
        )
        result = await self.session.scalars(ordered.limit(limit).offset(offset))
        return list(result.all()), total or 0

    def _apply_filters(
        self, statement: Select[tuple[ModelT]], filters: dict[str, object]
    ) -> Select[tuple[ModelT]]:
        return statement


class BomSpecificationRepository(BomQueryRepository[BomSpecificationModel]):
    sortable_fields = {
        "created_at": BomSpecificationModel.created_at,
        "updated_at": BomSpecificationModel.updated_at,
        "code": BomSpecificationModel.code,
        "name": BomSpecificationModel.name,
        "status": BomSpecificationModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BomSpecificationModel)

    def _apply_filters(
        self, statement: Select[tuple[BomSpecificationModel]], filters: dict[str, object]
    ) -> Select[tuple[BomSpecificationModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(BomSpecificationModel.organization_id == organization_id)
        if product_item_id := filters.get("product_item_id"):
            statement = statement.where(BomSpecificationModel.product_item_id == product_item_id)
        if status := filters.get("status"):
            statement = statement.where(BomSpecificationModel.status == status)
        if filters.get("is_active") is not None:
            statement = statement.where(BomSpecificationModel.is_active == filters["is_active"])
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(BomSpecificationModel.code.ilike(like), BomSpecificationModel.name.ilike(like))
            )
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            BomSpecificationModel.organization_id == organization_id,
            BomSpecificationModel.code == code,
        ]
        if exclude_id:
            conditions.append(BomSpecificationModel.id != exclude_id)
        return await self.exists(*conditions)


class BomVersionRepository(BomQueryRepository[BomVersionModel]):
    sortable_fields = {
        "created_at": BomVersionModel.created_at,
        "updated_at": BomVersionModel.updated_at,
        "version_number": BomVersionModel.version_number,
        "status": BomVersionModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BomVersionModel)

    def _apply_filters(
        self, statement: Select[tuple[BomVersionModel]], filters: dict[str, object]
    ) -> Select[tuple[BomVersionModel]]:
        if bom_id := filters.get("bom_id"):
            statement = statement.where(BomVersionModel.bom_id == bom_id)
        if status := filters.get("status"):
            statement = statement.where(BomVersionModel.status == status)
        return statement

    async def list_for_specification(self, bom_id: UUID) -> list[BomVersionModel]:
        result = await self.session.scalars(
            select(BomVersionModel)
            .where(BomVersionModel.bom_id == bom_id)
            .order_by(BomVersionModel.version_number.desc())
        )
        return list(result.all())

    async def max_version_number(self, bom_id: UUID) -> int:
        number = await self.session.scalar(
            select(func.max(BomVersionModel.version_number)).where(BomVersionModel.bom_id == bom_id)
        )
        return number or 0


class BomLineRepository(BomQueryRepository[BomLineModel]):
    sortable_fields = {
        "created_at": BomLineModel.created_at,
        "line_number": BomLineModel.line_number,
        "sort_order": BomLineModel.sort_order,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BomLineModel)

    async def list_for_version(self, version_id: UUID) -> list[BomLineModel]:
        result = await self.session.scalars(
            select(BomLineModel)
            .where(BomLineModel.bom_version_id == version_id)
            .order_by(BomLineModel.sort_order.asc(), BomLineModel.line_number.asc())
        )
        return list(result.all())

    async def next_line_number(self, version_id: UUID) -> int:
        number = await self.session.scalar(
            select(func.max(BomLineModel.line_number)).where(
                BomLineModel.bom_version_id == version_id
            )
        )
        return (number or 0) + 1

    async def get_for_version(self, version_id: UUID, line_id: UUID) -> BomLineModel | None:
        return cast(
            BomLineModel | None,
            await self.session.scalar(
                select(BomLineModel).where(
                    BomLineModel.bom_version_id == version_id,
                    BomLineModel.id == line_id,
                )
            ),
        )

    async def by_ids(self, line_ids: Sequence[UUID]) -> list[BomLineModel]:
        if not line_ids:
            return []
        result = await self.session.scalars(
            select(BomLineModel).where(BomLineModel.id.in_(line_ids))
        )
        return list(result.all())


class BomAttachmentRepository(BomQueryRepository[BomAttachmentModel]):
    sortable_fields = {"created_at": BomAttachmentModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, BomAttachmentModel)

    async def list_for_version(self, version_id: UUID) -> list[BomAttachmentModel]:
        result = await self.session.scalars(
            select(BomAttachmentModel)
            .where(
                BomAttachmentModel.bom_version_id == version_id,
                BomAttachmentModel.deleted_at.is_(None),
            )
            .order_by(BomAttachmentModel.created_at.desc())
        )
        return list(result.all())
