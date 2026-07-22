from __future__ import annotations

from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase
from app.modules.cnc.application.services.work_orders import CncWorkOrderService
from app.modules.cnc.domain.entities import CncWorkOrderStatus
from app.modules.cnc.infrastructure.repositories import CncWorkOrderRepository
from app.schemas.pagination import PageRequest, SortDirection


class CncQueueService(CncServiceBase):
    async def queue(self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id,
            CncWorkOrderStatus.QUEUED.value,
            actor_id=actor_id,
            user=user,
        )

    async def list_queue(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str = "queue_position",
        sort_direction: SortDirection = SortDirection.ASC,
        user: Any | None = None,
    ):
        filters = {**filters, "status": CncWorkOrderStatus.QUEUED.value}
        return await CncWorkOrderService(self.unit_of_work).list_orders(
            filters=filters,
            page=page,
            sort_by=sort_by,
            sort_direction=sort_direction,
            user=user,
        )

    async def reorder(
        self,
        machine_id: UUID,
        ordered_work_order_ids: list[UUID],
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> None:
        machine = await self.get_machine(machine_id)
        await self.ensure_site_access(user, machine.site_id)
        for position, work_order_id in enumerate(ordered_work_order_ids, start=1):
            work_order = await self.get_work_order(work_order_id)
            await self.ensure_work_order_scope(work_order, user)
            if (
                work_order.machine_id != machine_id
                or work_order.status != CncWorkOrderStatus.QUEUED.value
            ):
                raise ValidationError(
                    "Only queued work orders for selected machine can be reordered."
                )
            work_order.queue_position = position
            await CncWorkOrderRepository(self.session).update(work_order)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_queue",
            entity_id=machine_id,
            actor_id=actor_id,
            after={"ordered_work_order_ids": [str(item) for item in ordered_work_order_ids]},
        )
        await self.unit_of_work.commit()

    async def change_machine(
        self,
        work_order_id: UUID,
        machine_id: UUID,
        *,
        actor_id: UUID,
        user: Any | None = None,
    ):
        work_order = await self.get_work_order(work_order_id)
        await self.ensure_work_order_scope(work_order, user)
        await self.ensure_work_order_editable(work_order)
        if work_order.status in {CncWorkOrderStatus.RUNNING.value, CncWorkOrderStatus.SETUP.value}:
            raise ConflictError("Running CNC work order cannot change machine.")
        machine = await self.get_machine(machine_id)
        if (
            machine.organization_id != work_order.organization_id
            or machine.site_id != work_order.site_id
        ):
            raise ValidationError("Machine must belong to CNC work-order site.")
        await self.ensure_machine_ready_for_new_work(machine)
        program = await self.get_program(work_order.program_id) if work_order.program_id else None
        await self.ensure_program_compatible(program, machine)
        before = {"machine_id": str(work_order.machine_id) if work_order.machine_id else None}
        work_order.machine_id = machine.id
        if work_order.status == CncWorkOrderStatus.QUEUED.value:
            work_order.queue_position = (
                await CncWorkOrderRepository(self.session).max_queue_position(machine.id) + 1
            )
        await CncWorkOrderRepository(self.session).update(work_order)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_work_order",
            entity_id=work_order.id,
            actor_id=actor_id,
            before=before,
            after={"machine_id": str(machine.id)},
        )
        await self.commit_refresh(work_order)
        return work_order
