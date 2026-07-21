from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.production.infrastructure.models import (
    ProductionCompletionModel,
    ProductionMaterialRequirementModel,
    ProductionMaterialReservationModel,
    ProductionMaterialTransactionLineModel,
    ProductionMaterialTransactionModel,
    ProductionOrderBomSnapshotModel,
    ProductionOrderCommentModel,
    ProductionOrderModel,
    ProductionOrderStageModel,
    ProductionOutputSerialModel,
    ProductionStageTemplateModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection

ProductionModel = (
    ProductionOrderModel
    | ProductionOrderBomSnapshotModel
    | ProductionMaterialRequirementModel
    | ProductionMaterialReservationModel
    | ProductionStageTemplateModel
    | ProductionOrderStageModel
    | ProductionMaterialTransactionModel
    | ProductionMaterialTransactionLineModel
    | ProductionCompletionModel
    | ProductionOutputSerialModel
    | ProductionOrderCommentModel
)


class ProductionQueryRepository[ModelT: ProductionModel]:
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


class ProductionOrderRepository(ProductionQueryRepository[ProductionOrderModel]):
    sortable_fields = {
        "created_at": ProductionOrderModel.created_at,
        "updated_at": ProductionOrderModel.updated_at,
        "order_number": ProductionOrderModel.order_number,
        "status": ProductionOrderModel.status,
        "priority": ProductionOrderModel.priority,
        "planned_start_date": ProductionOrderModel.planned_start_date,
        "planned_end_date": ProductionOrderModel.planned_end_date,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionOrderModel)

    def _apply_filters(
        self, statement: Select[tuple[ProductionOrderModel]], filters: dict[str, object]
    ) -> Select[tuple[ProductionOrderModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(ProductionOrderModel.organization_id == organization_id)
        if status := filters.get("status"):
            statement = statement.where(ProductionOrderModel.status == status)
        if priority := filters.get("priority"):
            statement = statement.where(ProductionOrderModel.priority == priority)
        if site_id := filters.get("site_id"):
            statement = statement.where(ProductionOrderModel.site_id == site_id)
        if department_id := filters.get("department_id"):
            statement = statement.where(ProductionOrderModel.department_id == department_id)
        if product_item_id := filters.get("product_item_id"):
            statement = statement.where(ProductionOrderModel.product_item_id == product_item_id)
        if responsible_employee_id := filters.get("responsible_employee_id"):
            statement = statement.where(
                ProductionOrderModel.responsible_employee_id == responsible_employee_id
            )
        if filters.get("is_active") is not None:
            statement = statement.where(ProductionOrderModel.is_active == filters["is_active"])
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(
                    ProductionOrderModel.order_number.ilike(like),
                    ProductionOrderModel.name.ilike(like),
                )
            )
        site_ids = _sequence_filter(filters.get("site_ids"))
        if site_ids:
            statement = statement.where(ProductionOrderModel.site_id.in_(site_ids))
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(
                or_(
                    ProductionOrderModel.material_warehouse_id.in_(warehouse_ids),
                    ProductionOrderModel.finished_goods_warehouse_id.in_(warehouse_ids),
                    ProductionOrderModel.production_warehouse_id.in_(warehouse_ids),
                )
            )
        return statement

    async def exists_by_number(
        self, organization_id: UUID, order_number: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            ProductionOrderModel.organization_id == organization_id,
            ProductionOrderModel.order_number == order_number,
        ]
        if exclude_id:
            conditions.append(ProductionOrderModel.id != exclude_id)
        return await self.exists(*conditions)

    async def next_sequence(self, organization_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(ProductionOrderModel)
            .where(ProductionOrderModel.organization_id == organization_id)
        )
        return (total or 0) + 1


class ProductionSnapshotRepository(ProductionQueryRepository[ProductionOrderBomSnapshotModel]):
    sortable_fields = {"created_at": ProductionOrderBomSnapshotModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionOrderBomSnapshotModel)

    async def get_for_order(self, order_id: UUID) -> ProductionOrderBomSnapshotModel | None:
        return cast(
            ProductionOrderBomSnapshotModel | None,
            await self.session.scalar(
                select(ProductionOrderBomSnapshotModel).where(
                    ProductionOrderBomSnapshotModel.production_order_id == order_id
                )
            ),
        )


class ProductionRequirementRepository(
    ProductionQueryRepository[ProductionMaterialRequirementModel]
):
    sortable_fields = {
        "created_at": ProductionMaterialRequirementModel.created_at,
        "line_number": ProductionMaterialRequirementModel.line_number,
        "sort_order": ProductionMaterialRequirementModel.sort_order,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionMaterialRequirementModel)

    async def list_for_order(self, order_id: UUID) -> list[ProductionMaterialRequirementModel]:
        result = await self.session.scalars(
            select(ProductionMaterialRequirementModel)
            .where(ProductionMaterialRequirementModel.production_order_id == order_id)
            .order_by(
                ProductionMaterialRequirementModel.sort_order.asc(),
                ProductionMaterialRequirementModel.line_number.asc(),
            )
        )
        return list(result.all())

    async def get_for_order(
        self, order_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> ProductionMaterialRequirementModel | None:
        statement = select(ProductionMaterialRequirementModel).where(
            ProductionMaterialRequirementModel.production_order_id == order_id,
            ProductionMaterialRequirementModel.id == requirement_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(ProductionMaterialRequirementModel | None, await self.session.scalar(statement))


class ProductionReservationRepository(
    ProductionQueryRepository[ProductionMaterialReservationModel]
):
    sortable_fields = {"created_at": ProductionMaterialReservationModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionMaterialReservationModel)

    async def active_for_order(self, order_id: UUID) -> list[ProductionMaterialReservationModel]:
        result = await self.session.scalars(
            select(ProductionMaterialReservationModel).where(
                ProductionMaterialReservationModel.production_order_id == order_id,
                ProductionMaterialReservationModel.status == "active",
            )
        )
        return list(result.all())

    async def active_quantity_for_item(
        self, inventory_item_id: UUID, warehouse_id: UUID, *, exclude_order_id: UUID | None = None
    ) -> Any:
        statement = select(
            func.coalesce(func.sum(ProductionMaterialReservationModel.quantity), 0)
        ).where(
            ProductionMaterialReservationModel.inventory_item_id == inventory_item_id,
            ProductionMaterialReservationModel.warehouse_id == warehouse_id,
            ProductionMaterialReservationModel.status == "active",
        )
        if exclude_order_id:
            statement = statement.where(
                ProductionMaterialReservationModel.production_order_id != exclude_order_id
            )
        return await self.session.scalar(statement)


class ProductionStageRepository(ProductionQueryRepository[ProductionOrderStageModel]):
    sortable_fields = {
        "created_at": ProductionOrderStageModel.created_at,
        "sequence": ProductionOrderStageModel.sequence,
        "status": ProductionOrderStageModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionOrderStageModel)

    async def list_for_order(self, order_id: UUID) -> list[ProductionOrderStageModel]:
        result = await self.session.scalars(
            select(ProductionOrderStageModel)
            .where(ProductionOrderStageModel.production_order_id == order_id)
            .order_by(ProductionOrderStageModel.sequence.asc())
        )
        return list(result.all())


class ProductionStageTemplateRepository(ProductionQueryRepository[ProductionStageTemplateModel]):
    sortable_fields = {
        "created_at": ProductionStageTemplateModel.created_at,
        "code": ProductionStageTemplateModel.code,
        "name": ProductionStageTemplateModel.name,
        "default_sequence": ProductionStageTemplateModel.default_sequence,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionStageTemplateModel)

    def _apply_filters(
        self, statement: Select[tuple[ProductionStageTemplateModel]], filters: dict[str, object]
    ) -> Select[tuple[ProductionStageTemplateModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(
                ProductionStageTemplateModel.organization_id == organization_id
            )
        if filters.get("is_active") is not None:
            statement = statement.where(
                ProductionStageTemplateModel.is_active == filters["is_active"]
            )
        return statement


class ProductionTransactionRepository(
    ProductionQueryRepository[ProductionMaterialTransactionModel]
):
    sortable_fields = {"created_at": ProductionMaterialTransactionModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionMaterialTransactionModel)

    async def list_for_order(self, order_id: UUID) -> list[ProductionMaterialTransactionModel]:
        result = await self.session.scalars(
            select(ProductionMaterialTransactionModel)
            .where(ProductionMaterialTransactionModel.production_order_id == order_id)
            .order_by(ProductionMaterialTransactionModel.created_at.desc())
        )
        return list(result.all())


class ProductionTransactionLineRepository(
    ProductionQueryRepository[ProductionMaterialTransactionLineModel]
):
    sortable_fields = {"created_at": ProductionMaterialTransactionLineModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionMaterialTransactionLineModel)


class ProductionCompletionRepository(ProductionQueryRepository[ProductionCompletionModel]):
    sortable_fields = {
        "created_at": ProductionCompletionModel.created_at,
        "posted_at": ProductionCompletionModel.posted_at,
        "completion_number": ProductionCompletionModel.completion_number,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionCompletionModel)

    async def list_for_order(self, order_id: UUID) -> list[ProductionCompletionModel]:
        result = await self.session.scalars(
            select(ProductionCompletionModel)
            .where(ProductionCompletionModel.production_order_id == order_id)
            .order_by(ProductionCompletionModel.completion_number.asc())
        )
        return list(result.all())

    async def next_completion_number(self, order_id: UUID) -> int:
        number = await self.session.scalar(
            select(func.max(ProductionCompletionModel.completion_number)).where(
                ProductionCompletionModel.production_order_id == order_id
            )
        )
        return (number or 0) + 1


class ProductionOutputSerialRepository(ProductionQueryRepository[ProductionOutputSerialModel]):
    sortable_fields = {"created_at": ProductionOutputSerialModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionOutputSerialModel)

    async def exists_by_serial_number(self, serial_number: str) -> bool:
        return await self.exists(
            ProductionOutputSerialModel.serial_number_snapshot == serial_number
        )


class ProductionCommentRepository(ProductionQueryRepository[ProductionOrderCommentModel]):
    sortable_fields = {"created_at": ProductionOrderCommentModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ProductionOrderCommentModel)

    async def list_for_order(self, order_id: UUID) -> list[ProductionOrderCommentModel]:
        result = await self.session.scalars(
            select(ProductionOrderCommentModel)
            .where(
                ProductionOrderCommentModel.production_order_id == order_id,
                ProductionOrderCommentModel.deleted_at.is_(None),
            )
            .order_by(ProductionOrderCommentModel.created_at.asc())
        )
        return list(result.all())


def _sequence_filter(value: object) -> Sequence[Any] | None:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return None
