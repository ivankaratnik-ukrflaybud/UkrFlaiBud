from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.cnc.infrastructure.models import (
    CncExecutionLogModel,
    CncMachineModel,
    CncMaterialTransactionModel,
    CncOffcutModel,
    CncPartModel,
    CncProgramModel,
    CncSheetPlanLineModel,
    CncSheetPlanModel,
    CncToolModel,
    CncWorkOrderCommentModel,
    CncWorkOrderModel,
    CncWorkOrderOutputModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection

CncModel = (
    CncMachineModel
    | CncToolModel
    | CncProgramModel
    | CncPartModel
    | CncSheetPlanModel
    | CncSheetPlanLineModel
    | CncWorkOrderModel
    | CncWorkOrderOutputModel
    | CncExecutionLogModel
    | CncMaterialTransactionModel
    | CncOffcutModel
    | CncWorkOrderCommentModel
)


class CncQueryRepository[ModelT: CncModel]:
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
        if organization_id := filters.get("organization_id"):
            model = cast(Any, self.model)
            statement = statement.where(model.organization_id == organization_id)
        return statement


class CncMachineRepository(CncQueryRepository[CncMachineModel]):
    sortable_fields = {
        "created_at": CncMachineModel.created_at,
        "updated_at": CncMachineModel.updated_at,
        "code": CncMachineModel.code,
        "name": CncMachineModel.name,
        "status": CncMachineModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncMachineModel)

    def _apply_filters(
        self, statement: Select[tuple[CncMachineModel]], filters: dict[str, object]
    ) -> Select[tuple[CncMachineModel]]:
        statement = super()._apply_filters(statement, filters)
        if site_id := filters.get("site_id"):
            statement = statement.where(CncMachineModel.site_id == site_id)
        if status := filters.get("status"):
            statement = statement.where(CncMachineModel.status == status)
        if machine_type := filters.get("machine_type"):
            statement = statement.where(CncMachineModel.machine_type == machine_type)
        if filters.get("is_active") is not None:
            statement = statement.where(CncMachineModel.is_active == filters["is_active"])
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(CncMachineModel.code.ilike(like), CncMachineModel.name.ilike(like))
            )
        site_ids = _sequence_filter(filters.get("site_ids"))
        if site_ids:
            statement = statement.where(CncMachineModel.site_id.in_(site_ids))
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            CncMachineModel.organization_id == organization_id,
            CncMachineModel.code == code,
        ]
        if exclude_id:
            conditions.append(CncMachineModel.id != exclude_id)
        return await self.exists(*conditions)


class CncToolRepository(CncQueryRepository[CncToolModel]):
    sortable_fields = {
        "created_at": CncToolModel.created_at,
        "updated_at": CncToolModel.updated_at,
        "code": CncToolModel.code,
        "name": CncToolModel.name,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncToolModel)

    def _apply_filters(
        self, statement: Select[tuple[CncToolModel]], filters: dict[str, object]
    ) -> Select[tuple[CncToolModel]]:
        statement = super()._apply_filters(statement, filters)
        if tool_type := filters.get("tool_type"):
            statement = statement.where(CncToolModel.tool_type == tool_type)
        if filters.get("is_active") is not None:
            statement = statement.where(CncToolModel.is_active == filters["is_active"])
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            CncToolModel.organization_id == organization_id,
            CncToolModel.code == code,
        ]
        if exclude_id:
            conditions.append(CncToolModel.id != exclude_id)
        return await self.exists(*conditions)


class CncProgramRepository(CncQueryRepository[CncProgramModel]):
    sortable_fields = {
        "created_at": CncProgramModel.created_at,
        "updated_at": CncProgramModel.updated_at,
        "code": CncProgramModel.code,
        "revision": CncProgramModel.revision,
        "program_status": CncProgramModel.program_status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncProgramModel)

    def _apply_filters(
        self, statement: Select[tuple[CncProgramModel]], filters: dict[str, object]
    ) -> Select[tuple[CncProgramModel]]:
        statement = super()._apply_filters(statement, filters)
        if status := filters.get("program_status"):
            statement = statement.where(CncProgramModel.program_status == status)
        if machine_type := filters.get("machine_type"):
            statement = statement.where(CncProgramModel.machine_type == machine_type)
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(CncProgramModel.code.ilike(like), CncProgramModel.name.ilike(like))
            )
        return statement

    async def exists_revision(
        self,
        organization_id: UUID,
        code: str,
        revision: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        conditions: list[Any] = [
            CncProgramModel.organization_id == organization_id,
            CncProgramModel.code == code,
            CncProgramModel.revision == revision,
        ]
        if exclude_id:
            conditions.append(CncProgramModel.id != exclude_id)
        return await self.exists(*conditions)


class CncPartRepository(CncQueryRepository[CncPartModel]):
    sortable_fields = {
        "created_at": CncPartModel.created_at,
        "updated_at": CncPartModel.updated_at,
        "code": CncPartModel.code,
        "name": CncPartModel.name,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncPartModel)

    def _apply_filters(
        self, statement: Select[tuple[CncPartModel]], filters: dict[str, object]
    ) -> Select[tuple[CncPartModel]]:
        statement = super()._apply_filters(statement, filters)
        if filters.get("is_active") is not None:
            statement = statement.where(CncPartModel.is_active == filters["is_active"])
        if material_item_id := filters.get("material_item_id"):
            statement = statement.where(CncPartModel.material_item_id == material_item_id)
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(CncPartModel.code.ilike(like), CncPartModel.name.ilike(like))
            )
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            CncPartModel.organization_id == organization_id,
            CncPartModel.code == code,
        ]
        if exclude_id:
            conditions.append(CncPartModel.id != exclude_id)
        return await self.exists(*conditions)


class CncSheetPlanRepository(CncQueryRepository[CncSheetPlanModel]):
    sortable_fields = {
        "created_at": CncSheetPlanModel.created_at,
        "updated_at": CncSheetPlanModel.updated_at,
        "plan_number": CncSheetPlanModel.plan_number,
        "status": CncSheetPlanModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncSheetPlanModel)

    def _apply_filters(
        self, statement: Select[tuple[CncSheetPlanModel]], filters: dict[str, object]
    ) -> Select[tuple[CncSheetPlanModel]]:
        statement = super()._apply_filters(statement, filters)
        if status := filters.get("status"):
            statement = statement.where(CncSheetPlanModel.status == status)
        if material_item_id := filters.get("material_item_id"):
            statement = statement.where(CncSheetPlanModel.material_item_id == material_item_id)
        if production_order_id := filters.get("production_order_id"):
            statement = statement.where(
                CncSheetPlanModel.production_order_id == production_order_id
            )
        return statement

    async def exists_by_number(
        self, organization_id: UUID, plan_number: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            CncSheetPlanModel.organization_id == organization_id,
            CncSheetPlanModel.plan_number == plan_number,
        ]
        if exclude_id:
            conditions.append(CncSheetPlanModel.id != exclude_id)
        return await self.exists(*conditions)


class CncSheetPlanLineRepository(CncQueryRepository[CncSheetPlanLineModel]):
    sortable_fields = {
        "created_at": CncSheetPlanLineModel.created_at,
        "sort_order": CncSheetPlanLineModel.sort_order,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncSheetPlanLineModel)

    async def list_for_plan(self, sheet_plan_id: UUID) -> list[CncSheetPlanLineModel]:
        result = await self.session.scalars(
            select(CncSheetPlanLineModel)
            .where(CncSheetPlanLineModel.sheet_plan_id == sheet_plan_id)
            .order_by(CncSheetPlanLineModel.sort_order.asc())
        )
        return list(result.all())


class CncWorkOrderRepository(CncQueryRepository[CncWorkOrderModel]):
    sortable_fields = {
        "created_at": CncWorkOrderModel.created_at,
        "updated_at": CncWorkOrderModel.updated_at,
        "work_order_number": CncWorkOrderModel.work_order_number,
        "status": CncWorkOrderModel.status,
        "priority": CncWorkOrderModel.priority,
        "planned_start_at": CncWorkOrderModel.planned_start_at,
        "queue_position": CncWorkOrderModel.queue_position,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncWorkOrderModel)

    def _apply_filters(
        self, statement: Select[tuple[CncWorkOrderModel]], filters: dict[str, object]
    ) -> Select[tuple[CncWorkOrderModel]]:
        statement = super()._apply_filters(statement, filters)
        for key, column in {
            "status": CncWorkOrderModel.status,
            "priority": CncWorkOrderModel.priority,
            "machine_id": CncWorkOrderModel.machine_id,
            "site_id": CncWorkOrderModel.site_id,
            "production_order_id": CncWorkOrderModel.production_order_id,
            "material_item_id": CncWorkOrderModel.material_item_id,
            "cnc_part_id": CncWorkOrderModel.cnc_part_id,
            "operator_employee_id": CncWorkOrderModel.operator_employee_id,
        }.items():
            if value := filters.get(key):
                statement = statement.where(column == value)
        if filters.get("blocked"):
            statement = statement.where(CncWorkOrderModel.status == "blocked")
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(
                    CncWorkOrderModel.work_order_number.ilike(like),
                    CncWorkOrderModel.name.ilike(like),
                    CncWorkOrderModel.part_name_snapshot.ilike(like),
                )
            )
        site_ids = _sequence_filter(filters.get("site_ids"))
        if site_ids:
            statement = statement.where(CncWorkOrderModel.site_id.in_(site_ids))
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(
                or_(
                    CncWorkOrderModel.source_warehouse_id.in_(warehouse_ids),
                    CncWorkOrderModel.output_warehouse_id.in_(warehouse_ids),
                )
            )
        return statement

    async def exists_by_number(
        self, organization_id: UUID, work_order_number: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            CncWorkOrderModel.organization_id == organization_id,
            CncWorkOrderModel.work_order_number == work_order_number,
        ]
        if exclude_id:
            conditions.append(CncWorkOrderModel.id != exclude_id)
        return await self.exists(*conditions)

    async def running_for_machine(
        self, machine_id: UUID, *, exclude_id: UUID | None = None
    ) -> CncWorkOrderModel | None:
        statement = select(CncWorkOrderModel).where(
            CncWorkOrderModel.machine_id == machine_id,
            CncWorkOrderModel.status.in_(["setup", "running"]),
            CncWorkOrderModel.deleted_at.is_(None),
        )
        if exclude_id:
            statement = statement.where(CncWorkOrderModel.id != exclude_id)
        return cast(CncWorkOrderModel | None, await self.session.scalar(statement))

    async def max_queue_position(self, machine_id: UUID) -> int:
        value = await self.session.scalar(
            select(func.max(CncWorkOrderModel.queue_position)).where(
                CncWorkOrderModel.machine_id == machine_id,
                CncWorkOrderModel.status == "queued",
            )
        )
        return int(value or 0)

    async def next_sequence(self, organization_id: UUID) -> int:
        total = await self.session.scalar(
            select(func.count())
            .select_from(CncWorkOrderModel)
            .where(CncWorkOrderModel.organization_id == organization_id)
        )
        return (total or 0) + 1


class CncWorkOrderOutputRepository(CncQueryRepository[CncWorkOrderOutputModel]):
    sortable_fields = {"created_at": CncWorkOrderOutputModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncWorkOrderOutputModel)

    async def list_for_work_order(self, work_order_id: UUID) -> list[CncWorkOrderOutputModel]:
        result = await self.session.scalars(
            select(CncWorkOrderOutputModel).where(
                CncWorkOrderOutputModel.work_order_id == work_order_id
            )
        )
        return list(result.all())


class CncExecutionLogRepository(CncQueryRepository[CncExecutionLogModel]):
    sortable_fields = {"created_at": CncExecutionLogModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncExecutionLogModel)

    async def list_for_work_order(self, work_order_id: UUID) -> list[CncExecutionLogModel]:
        result = await self.session.scalars(
            select(CncExecutionLogModel)
            .where(CncExecutionLogModel.work_order_id == work_order_id)
            .order_by(CncExecutionLogModel.event_at.asc())
        )
        return list(result.all())


class CncMaterialTransactionRepository(CncQueryRepository[CncMaterialTransactionModel]):
    sortable_fields = {"created_at": CncMaterialTransactionModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncMaterialTransactionModel)

    async def list_for_work_order(self, work_order_id: UUID) -> list[CncMaterialTransactionModel]:
        result = await self.session.scalars(
            select(CncMaterialTransactionModel)
            .where(CncMaterialTransactionModel.work_order_id == work_order_id)
            .order_by(CncMaterialTransactionModel.posted_at.asc())
        )
        return list(result.all())


class CncOffcutRepository(CncQueryRepository[CncOffcutModel]):
    sortable_fields = {
        "created_at": CncOffcutModel.created_at,
        "updated_at": CncOffcutModel.updated_at,
        "offcut_code": CncOffcutModel.offcut_code,
        "status": CncOffcutModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CncOffcutModel)

    def _apply_filters(
        self, statement: Select[tuple[CncOffcutModel]], filters: dict[str, object]
    ) -> Select[tuple[CncOffcutModel]]:
        statement = super()._apply_filters(statement, filters)
        if status := filters.get("status"):
            statement = statement.where(CncOffcutModel.status == status)
        if material_item_id := filters.get("material_item_id"):
            statement = statement.where(CncOffcutModel.material_item_id == material_item_id)
        if warehouse_id := filters.get("warehouse_id"):
            statement = statement.where(CncOffcutModel.warehouse_id == warehouse_id)
        return statement


def _sequence_filter(value: object) -> Sequence[Any] | None:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return None
