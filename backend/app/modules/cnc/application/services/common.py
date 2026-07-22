from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditLog
from app.database.outbox import OutboxEvent
from app.models.base import (
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.cnc.domain.entities import (
    CncMachineStatus,
    CncProgramStatus,
    CncWorkOrderStatus,
)
from app.modules.cnc.infrastructure.models import (
    CncMachineModel,
    CncPartModel,
    CncProgramModel,
    CncSheetPlanModel,
    CncWorkOrderModel,
)
from app.modules.cnc.infrastructure.repositories import (
    CncMachineRepository,
    CncPartRepository,
    CncProgramRepository,
    CncSheetPlanRepository,
    CncWorkOrderRepository,
)
from app.modules.inventory.application.services import DocumentService, InventoryScopeService
from app.modules.inventory.domain.entities import InventoryDocumentType
from app.modules.inventory.infrastructure.models import (
    ItemModel,
    SiteModel,
    UnitOfMeasureModel,
    WarehouseModel,
)
from app.modules.organizations.infrastructure.models import (
    DepartmentModel,
    EmployeeModel,
    OrganizationModel,
)
from app.repositories.sqlalchemy_audit import SQLAlchemyAuditLogRepository
from app.repositories.sqlalchemy_outbox import SQLAlchemyOutboxRepository
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

FINAL_WORK_ORDER_STATUSES = {CncWorkOrderStatus.COMPLETED.value, CncWorkOrderStatus.CANCELLED.value}
LOCKED_MACHINE_STATUSES = {
    CncMachineStatus.MAINTENANCE.value,
    CncMachineStatus.FAULT.value,
    CncMachineStatus.UNAVAILABLE.value,
    CncMachineStatus.DECOMMISSIONED.value,
}


class CncServiceBase:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def commit_refresh(self, entity: object) -> None:
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(entity)

    async def audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor_id: UUID | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await SQLAlchemyAuditLogRepository(self.session).create(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                before_data=before,
                after_data=after,
                correlation_id=None,
            )
        )

    async def outbox(
        self, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict[str, Any]
    ) -> None:
        await SQLAlchemyOutboxRepository(self.session).create(
            OutboxEvent(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                occurred_at=datetime.now(UTC),
            )
        )

    async def ensure_organization(self, organization_id: UUID) -> None:
        exists = await self.session.scalar(
            select(func.count())
            .select_from(OrganizationModel)
            .where(OrganizationModel.id == organization_id)
        )
        if not exists:
            raise EntityNotFoundError("Organization not found.", {"id": str(organization_id)})

    async def ensure_site(self, organization_id: UUID, site_id: UUID) -> SiteModel:
        site = await self.session.get(SiteModel, site_id)
        if site is None or site.deleted_at is not None:
            raise EntityNotFoundError("Site not found.", {"id": str(site_id)})
        if site.organization_id != organization_id:
            raise ValidationError("Site must belong to the same organization.")
        if not site.is_active:
            raise ValidationError("Inactive site cannot be used for CNC.")
        return site

    async def ensure_warehouse(
        self, organization_id: UUID, warehouse_id: UUID, *, site_id: UUID | None = None
    ) -> WarehouseModel:
        warehouse = await self.session.get(WarehouseModel, warehouse_id)
        if warehouse is None or warehouse.deleted_at is not None:
            raise EntityNotFoundError("Warehouse not found.", {"id": str(warehouse_id)})
        if warehouse.organization_id != organization_id:
            raise ValidationError("Warehouse must belong to the same organization.")
        if site_id is not None and warehouse.site_id != site_id:
            raise ValidationError("Warehouse must belong to the selected site.")
        if not warehouse.is_active:
            raise ValidationError("Inactive warehouse cannot be used for CNC.")
        return warehouse

    async def ensure_item(self, organization_id: UUID, item_id: UUID | None) -> ItemModel | None:
        if item_id is None:
            return None
        item = await self.session.get(ItemModel, item_id)
        if item is None or item.deleted_at is not None:
            raise EntityNotFoundError("Inventory item not found.", {"id": str(item_id)})
        if item.organization_id != organization_id:
            raise ValidationError("Inventory item must belong to the same organization.")
        if not item.is_active:
            raise ValidationError("Inactive item cannot be used for CNC.")
        return item

    async def ensure_unit(self, organization_id: UUID, unit_id: UUID) -> UnitOfMeasureModel:
        unit = await self.session.get(UnitOfMeasureModel, unit_id)
        if unit is None or unit.deleted_at is not None:
            raise EntityNotFoundError("Unit of measure not found.", {"id": str(unit_id)})
        if unit.organization_id != organization_id:
            raise ValidationError("Unit must belong to the same organization.")
        return unit

    async def ensure_employee(self, organization_id: UUID, employee_id: UUID | None) -> None:
        if employee_id is None:
            return
        employee = await self.session.get(EmployeeModel, employee_id)
        if employee is None or employee.deleted_at is not None:
            raise EntityNotFoundError("Employee not found.", {"id": str(employee_id)})
        if employee.organization_id != organization_id:
            raise ValidationError("Employee must belong to the same organization.")

    async def ensure_department(self, organization_id: UUID, department_id: UUID | None) -> None:
        if department_id is None:
            return
        department = await self.session.get(DepartmentModel, department_id)
        if department is None or department.deleted_at is not None:
            raise EntityNotFoundError("Department not found.", {"id": str(department_id)})
        if department.organization_id != organization_id:
            raise ValidationError("Department must belong to the same organization.")

    async def ensure_site_access(self, user: Any | None, site_id: UUID) -> None:
        if user is None or getattr(user, "is_superuser", False):
            return
        allowed = await InventoryScopeService(self.unit_of_work).accessible_site_ids(user)
        if site_id not in (allowed or set()):
            raise PermissionDeniedError("You do not have access to this site.")

    async def ensure_warehouse_access(self, user: Any | None, *warehouse_ids: UUID | None) -> None:
        if user is None or getattr(user, "is_superuser", False):
            return
        scope = InventoryScopeService(self.unit_of_work)
        for warehouse_id in warehouse_ids:
            if warehouse_id is not None:
                await scope.ensure_warehouse_access(user, warehouse_id)

    async def get_machine(self, machine_id: UUID) -> CncMachineModel:
        machine = await CncMachineRepository(self.session).get(machine_id)
        if machine is None:
            raise EntityNotFoundError("CNC machine not found.", {"id": str(machine_id)})
        return machine

    async def get_program(self, program_id: UUID) -> CncProgramModel:
        program = await CncProgramRepository(self.session).get(program_id)
        if program is None:
            raise EntityNotFoundError("CNC program not found.", {"id": str(program_id)})
        return program

    async def get_part(self, part_id: UUID) -> CncPartModel:
        part = await CncPartRepository(self.session).get(part_id)
        if part is None:
            raise EntityNotFoundError("CNC part not found.", {"id": str(part_id)})
        return part

    async def get_sheet_plan(self, sheet_plan_id: UUID) -> CncSheetPlanModel:
        plan = await CncSheetPlanRepository(self.session).get(sheet_plan_id)
        if plan is None:
            raise EntityNotFoundError("CNC sheet plan not found.", {"id": str(sheet_plan_id)})
        return plan

    async def get_work_order(self, work_order_id: UUID) -> CncWorkOrderModel:
        work_order = await CncWorkOrderRepository(self.session).get(work_order_id)
        if work_order is None:
            raise EntityNotFoundError("CNC work order not found.", {"id": str(work_order_id)})
        return work_order

    async def ensure_work_order_scope(
        self, work_order: CncWorkOrderModel, user: Any | None
    ) -> None:
        await self.ensure_site_access(user, work_order.site_id)
        await self.ensure_warehouse_access(
            user, work_order.source_warehouse_id, work_order.output_warehouse_id
        )

    async def ensure_work_order_editable(self, work_order: CncWorkOrderModel) -> None:
        if work_order.status in FINAL_WORK_ORDER_STATUSES:
            raise ConflictError("Completed and cancelled CNC work orders are read-only.")

    async def ensure_machine_ready_for_new_work(self, machine: CncMachineModel) -> None:
        if not machine.is_active or machine.status in LOCKED_MACHINE_STATUSES:
            raise ConflictError("Machine cannot receive new CNC work.")

    async def ensure_program_compatible(
        self, program: CncProgramModel | None, machine: CncMachineModel | None
    ) -> None:
        if program is None or machine is None:
            return
        if program.program_status != CncProgramStatus.APPROVED.value:
            raise ValidationError("Program must be approved before machining.")
        if program.machine_type and program.machine_type != machine.machine_type:
            raise ValidationError("Program is not compatible with selected machine.")
        compatible = program.compatible_machine_ids or []
        if compatible and str(machine.id) not in {str(item) for item in compatible}:
            raise ValidationError("Program is not approved for selected machine.")

    async def inventory_document(
        self,
        *,
        organization_id: UUID,
        document_type: InventoryDocumentType,
        source_warehouse_id: UUID | None,
        destination_warehouse_id: UUID | None,
        item_id: UUID,
        quantity: Decimal,
        actor_id: UUID,
        user: Any | None,
        location_id: UUID | None = None,
        reference: str,
        notes: str | None = None,
    ) -> UUID:
        service = DocumentService(self.unit_of_work)
        document = await service.create_draft(
            {
                "organization_id": organization_id,
                "document_type": document_type.value,
                "source_warehouse_id": source_warehouse_id,
                "destination_warehouse_id": destination_warehouse_id,
                "responsible_employee_id": None,
                "reference": reference,
                "notes": notes,
            },
            actor_id=actor_id,
        )
        await service.add_line(
            document.id,
            {
                "item_id": item_id,
                "quantity": quantity,
                "source_location_id": location_id if source_warehouse_id else None,
                "destination_location_id": location_id if destination_warehouse_id else None,
                "lot_id": None,
                "notes": notes,
            },
            actor_id=actor_id,
        )
        await service.post(document.id, actor_id=actor_id, user=user)
        return document.id


def decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def apply_updates(entity: Any, data: dict[str, Any]) -> None:
    for key, value in data.items():
        setattr(entity, key, value)
