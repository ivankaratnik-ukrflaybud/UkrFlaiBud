from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates, decimal
from app.modules.cnc.domain.entities import CncExecutionEventType, CncWorkOrderStatus
from app.modules.cnc.infrastructure.models import (
    CncExecutionLogModel,
    CncWorkOrderModel,
    CncWorkOrderOutputModel,
)
from app.modules.cnc.infrastructure.repositories import (
    CncExecutionLogRepository,
    CncSheetPlanLineRepository,
    CncWorkOrderOutputRepository,
    CncWorkOrderRepository,
)
from app.schemas.pagination import PageRequest, SortDirection

ALLOWED_WORK_ORDER_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"planned", "cancelled"},
    "planned": {"queued", "cancelled"},
    "queued": {"setup", "blocked", "cancelled"},
    "setup": {"running", "blocked"},
    "running": {"paused", "partially_completed", "completed", "blocked"},
    "paused": {"running", "blocked"},
    "partially_completed": {"running", "completed"},
    "blocked": {"queued", "setup", "running", "cancelled"},
}


class CncWorkOrderService(CncServiceBase):
    async def create(
        self, data: dict[str, Any], *, actor_id: UUID, user: Any | None = None
    ) -> CncWorkOrderModel:
        planned_quantity = decimal(data["planned_quantity"])
        if planned_quantity <= 0:
            raise ValidationError("Planned quantity must be greater than zero.")
        organization_id = data["organization_id"]
        await self.ensure_organization(organization_id)
        await self.ensure_site(organization_id, data["site_id"])
        await self.ensure_site_access(user, data["site_id"])
        await self.ensure_warehouse(
            organization_id, data["source_warehouse_id"], site_id=data["site_id"]
        )
        await self.ensure_warehouse(
            organization_id, data["output_warehouse_id"], site_id=data["site_id"]
        )
        await self.ensure_warehouse_access(
            user, data["source_warehouse_id"], data["output_warehouse_id"]
        )
        await self.ensure_department(organization_id, data.get("department_id"))
        await self.ensure_employee(organization_id, data.get("operator_employee_id"))
        await self.ensure_employee(organization_id, data.get("responsible_employee_id"))
        await self.ensure_unit(organization_id, data["unit_of_measure_id"])
        material = await self.ensure_item(organization_id, data.get("material_item_id"))
        if material and not data.get("material_name_snapshot"):
            data["material_name_snapshot"] = material.name
        part = await self.get_part(data["cnc_part_id"]) if data.get("cnc_part_id") else None
        program = await self.get_program(data["program_id"]) if data.get("program_id") else None
        machine = await self.get_machine(data["machine_id"]) if data.get("machine_id") else None
        sheet_plan = (
            await self.get_sheet_plan(data["sheet_plan_id"]) if data.get("sheet_plan_id") else None
        )
        if machine:
            if machine.organization_id != organization_id:
                raise ValidationError("Machine must belong to the same organization.")
            if machine.site_id != data["site_id"]:
                raise ValidationError("Machine must belong to selected site.")
            await self.ensure_machine_ready_for_new_work(machine)
        if program and program.organization_id != organization_id:
            raise ValidationError("Program must belong to the same organization.")
        await self.ensure_program_compatible(program, machine)
        repository = CncWorkOrderRepository(self.session)
        number = data.get("work_order_number") or await self.next_work_order_number(organization_id)
        if await repository.exists_by_number(organization_id, number):
            raise ConflictError(
                "CNC work order number must be unique.", {"field": "work_order_number"}
            )
        if part:
            data.setdefault("part_code_snapshot", part.code)
            data.setdefault("part_name_snapshot", part.name)
            data.setdefault("drawing_revision_snapshot", part.drawing_revision)
        if program:
            data.setdefault("program_revision_snapshot", program.revision)
        name = data.pop("name", None) or f"{number} - {part.name if part else 'CNC'}"
        data.pop("work_order_number", None)
        work_order = await repository.create(
            CncWorkOrderModel(
                **data,
                work_order_number=number,
                name=name,
                created_by_user_id=actor_id,
            )
        )
        await self._create_outputs(
            work_order,
            part_id=part.id if part else None,
            sheet_plan_id=sheet_plan.id if sheet_plan else None,
        )
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_work_order",
            entity_id=work_order.id,
            actor_id=actor_id,
            after={"number": work_order.work_order_number, "status": work_order.status},
        )
        await self.outbox(
            "cnc.work_order.created",
            "cnc_work_order",
            work_order.id,
            {"work_order_number": work_order.work_order_number},
        )
        await self.commit_refresh(work_order)
        return work_order

    async def _create_outputs(
        self,
        work_order: CncWorkOrderModel,
        *,
        part_id: UUID | None,
        sheet_plan_id: UUID | None,
    ) -> None:
        output_repository = CncWorkOrderOutputRepository(self.session)
        if sheet_plan_id:
            for line in await CncSheetPlanLineRepository(self.session).list_for_plan(sheet_plan_id):
                part = await self.get_part(line.cnc_part_id)
                await output_repository.create(
                    CncWorkOrderOutputModel(
                        work_order_id=work_order.id,
                        cnc_part_id=part.id,
                        inventory_item_id=part.inventory_item_id,
                        part_code_snapshot=line.part_code_snapshot,
                        part_name_snapshot=line.part_name_snapshot,
                        drawing_revision_snapshot=line.drawing_revision_snapshot,
                        planned_quantity=line.total_planned_quantity,
                        unit_of_measure_id=work_order.unit_of_measure_id,
                    )
                )
            return
        if part_id:
            part = await self.get_part(part_id)
            await output_repository.create(
                CncWorkOrderOutputModel(
                    work_order_id=work_order.id,
                    cnc_part_id=part.id,
                    inventory_item_id=part.inventory_item_id,
                    part_code_snapshot=part.code,
                    part_name_snapshot=part.name,
                    drawing_revision_snapshot=part.drawing_revision,
                    planned_quantity=work_order.planned_quantity,
                    unit_of_measure_id=work_order.unit_of_measure_id,
                )
            )

    async def list_orders(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: Any | None = None,
    ) -> tuple[list[CncWorkOrderModel], int]:
        if user and not getattr(user, "is_superuser", False):
            from app.modules.inventory.application.services import InventoryScopeService

            scope = InventoryScopeService(self.unit_of_work)
            site_ids = await scope.accessible_site_ids(user)
            warehouse_ids = await scope.accessible_warehouse_ids(user)
            if not site_ids and not warehouse_ids:
                return [], 0
            filters = {
                **filters,
                "site_ids": site_ids or set(),
                "warehouse_ids": warehouse_ids or set(),
            }
        return await CncWorkOrderRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, work_order_id: UUID, *, user: Any | None = None) -> CncWorkOrderModel:
        work_order = await self.get_work_order(work_order_id)
        await self.ensure_work_order_scope(work_order, user)
        return work_order

    async def update(
        self,
        work_order_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
        user: Any | None = None,
    ) -> CncWorkOrderModel:
        work_order = await self.get(work_order_id, user=user)
        await self.ensure_work_order_editable(work_order)
        if expected_version is not None and work_order.version != expected_version:
            raise ConflictError("Entity version conflict.")
        locked = {"planned_quantity", "unit_of_measure_id", "cnc_part_id", "sheet_plan_id"}
        if work_order.status not in {
            CncWorkOrderStatus.DRAFT.value,
            CncWorkOrderStatus.PLANNED.value,
        }:
            if locked & data.keys():
                raise ConflictError("Queued or active CNC work orders require controlled revision.")
        apply_updates(work_order, data)
        await CncWorkOrderRepository(self.session).update(work_order)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_work_order",
            entity_id=work_order.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(work_order)
        return work_order

    async def transition(
        self,
        work_order_id: UUID,
        target_status: str,
        *,
        actor_id: UUID,
        user: Any | None = None,
        reason: str | None = None,
    ) -> CncWorkOrderModel:
        work_order = await self.get(work_order_id, user=user)
        await self.ensure_work_order_editable(work_order)
        source_status = work_order.status
        if target_status not in ALLOWED_WORK_ORDER_TRANSITIONS.get(source_status, set()):
            raise ConflictError("Invalid CNC work order status transition.")
        if (
            target_status in {CncWorkOrderStatus.BLOCKED.value, CncWorkOrderStatus.CANCELLED.value}
            and not reason
        ):
            raise ValidationError("Reason is required.")
        if target_status in {CncWorkOrderStatus.SETUP.value, CncWorkOrderStatus.RUNNING.value}:
            await self._ensure_can_run(work_order)
        now = datetime.now(UTC)
        work_order.status = target_status
        if target_status == CncWorkOrderStatus.QUEUED.value and work_order.machine_id:
            work_order.queue_position = (
                await CncWorkOrderRepository(self.session).max_queue_position(work_order.machine_id)
                + 1
            )
        if target_status == CncWorkOrderStatus.RUNNING.value and work_order.actual_start_at is None:
            work_order.actual_start_at = now
        if target_status == CncWorkOrderStatus.BLOCKED.value:
            work_order.blocked_reason = reason
        if target_status == CncWorkOrderStatus.CANCELLED.value:
            work_order.cancellation_reason = reason
            work_order.actual_end_at = now
        if target_status == CncWorkOrderStatus.COMPLETED.value:
            work_order.actual_end_at = now
            if work_order.completed_quantity + work_order.rejected_quantity <= 0:
                raise ValidationError("Completion requires reported output quantities.")
        await CncWorkOrderRepository(self.session).update(work_order)
        await self._log_transition(work_order, target_status, actor_id=actor_id, reason=reason)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_work_order",
            entity_id=work_order.id,
            actor_id=actor_id,
            before={"status": source_status},
            after={"status": target_status, "reason": reason},
        )
        event = {
            "queued": "cnc.work_order.queued",
            "running": "cnc.work_order.started",
            "blocked": "cnc.work_order.blocked",
            "completed": "cnc.work_order.completed",
        }.get(target_status)
        if event:
            await self.outbox(
                event,
                "cnc_work_order",
                work_order.id,
                {"work_order_number": work_order.work_order_number},
            )
        await self.commit_refresh(work_order)
        return work_order

    async def _ensure_can_run(self, work_order: CncWorkOrderModel) -> None:
        if not work_order.machine_id:
            raise ValidationError("Machine is required before CNC work can start.")
        machine = await self.get_machine(work_order.machine_id)
        await self.ensure_machine_ready_for_new_work(machine)
        running = await CncWorkOrderRepository(self.session).running_for_machine(
            machine.id, exclude_id=work_order.id
        )
        if running is not None:
            raise ConflictError("Machine already has a running CNC work order.")
        program = await self.get_program(work_order.program_id) if work_order.program_id else None
        await self.ensure_program_compatible(program, machine)
        if work_order.material_item_id and work_order.issued_material_quantity <= 0:
            raise ValidationError("Material must be issued before CNC machining starts.")

    async def _log_transition(
        self,
        work_order: CncWorkOrderModel,
        target_status: str,
        *,
        actor_id: UUID,
        reason: str | None,
    ) -> None:
        event_type = {
            "queued": CncExecutionEventType.QUEUED.value,
            "setup": CncExecutionEventType.SETUP_STARTED.value,
            "running": CncExecutionEventType.MACHINING_STARTED.value,
            "paused": CncExecutionEventType.PAUSED.value,
            "blocked": CncExecutionEventType.BLOCKED.value,
            "cancelled": CncExecutionEventType.CANCELLED.value,
            "completed": CncExecutionEventType.COMPLETED.value,
        }.get(target_status)
        if not event_type or not work_order.machine_id:
            return
        await CncExecutionLogRepository(self.session).create(
            CncExecutionLogModel(
                work_order_id=work_order.id,
                machine_id=work_order.machine_id,
                operator_employee_id=work_order.operator_employee_id,
                event_type=event_type,
                reason=reason,
                created_by_user_id=actor_id,
            )
        )

    async def next_work_order_number(self, organization_id: UUID) -> str:
        sequence = await CncWorkOrderRepository(self.session).next_sequence(organization_id)
        return f"CNC-{datetime.now(UTC):%Y%m%d}-{sequence:05d}"
