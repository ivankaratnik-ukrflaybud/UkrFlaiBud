from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, EntityNotFoundError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase, decimal
from app.modules.cnc.domain.entities import (
    CncExecutionEventType,
    CncOffcutStatus,
    CncWorkOrderStatus,
)
from app.modules.cnc.infrastructure.models import CncExecutionLogModel, CncOffcutModel
from app.modules.cnc.infrastructure.repositories import (
    CncExecutionLogRepository,
    CncOffcutRepository,
    CncWorkOrderOutputRepository,
    CncWorkOrderRepository,
)
from app.modules.inventory.domain.entities import InventoryDocumentType
from app.modules.production.domain.entities import ProductionOrderStatus
from app.modules.production.infrastructure.models import ProductionCompletionModel
from app.modules.production.infrastructure.repositories import (
    ProductionCompletionRepository,
    ProductionOrderRepository,
)


class CncOutputService(CncServiceBase):
    async def outputs(self, work_order_id: UUID):
        await self.get_work_order(work_order_id)
        return await CncWorkOrderOutputRepository(self.session).list_for_work_order(work_order_id)

    async def report_output(
        self, work_order_id: UUID, data: dict[str, Any], *, actor_id: UUID, user: Any | None = None
    ):
        work_order = await self.get_work_order(work_order_id)
        await self.ensure_work_order_scope(work_order, user)
        await self.ensure_work_order_editable(work_order)
        good = decimal(data.get("good_quantity", 0))
        rejected = decimal(data.get("rejected_quantity", 0))
        if good + rejected <= 0:
            raise ValidationError("Good plus rejected quantity must be greater than zero.")
        remaining = (
            work_order.planned_quantity
            - work_order.completed_quantity
            - work_order.rejected_quantity
        )
        if good + rejected > remaining and not data.get("allow_overproduction"):
            raise ConflictError("Cannot report above planned CNC quantity without permission.")
        outputs = await CncWorkOrderOutputRepository(self.session).list_for_work_order(
            work_order.id
        )
        output = None
        if data.get("output_id"):
            output = next((item for item in outputs if item.id == data["output_id"]), None)
            if output is None:
                raise EntityNotFoundError(
                    "CNC output line not found.", {"id": str(data["output_id"])}
                )
        elif outputs:
            output = outputs[0]
        if output is not None:
            output.completed_quantity += good
            output.rejected_quantity += rejected
            await CncWorkOrderOutputRepository(self.session).update(output)
        work_order.completed_quantity += good
        work_order.rejected_quantity += rejected
        if work_order.status == CncWorkOrderStatus.RUNNING.value and good + rejected < remaining:
            work_order.status = CncWorkOrderStatus.PARTIALLY_COMPLETED.value
        await CncWorkOrderRepository(self.session).update(work_order)
        if work_order.machine_id:
            await CncExecutionLogRepository(self.session).create(
                CncExecutionLogModel(
                    work_order_id=work_order.id,
                    machine_id=work_order.machine_id,
                    operator_employee_id=work_order.operator_employee_id,
                    event_type=CncExecutionEventType.QUANTITY_REPORTED.value,
                    quantity_good=good,
                    quantity_rejected=rejected,
                    reason=data.get("rejection_reason"),
                    notes=data.get("notes"),
                    created_by_user_id=actor_id,
                )
            )
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_work_order",
            entity_id=work_order.id,
            actor_id=actor_id,
            after={"good": str(good), "rejected": str(rejected)},
        )
        await self.commit_refresh(work_order)
        return work_order

    async def receipt_output(
        self, work_order_id: UUID, output_id: UUID, *, actor_id: UUID, user: Any | None = None
    ):
        try:
            work_order = await self.get_work_order(work_order_id)
            await self.ensure_work_order_scope(work_order, user)
            output = next(
                (
                    item
                    for item in await CncWorkOrderOutputRepository(
                        self.session
                    ).list_for_work_order(work_order.id)
                    if item.id == output_id
                ),
                None,
            )
            if output is None:
                raise EntityNotFoundError("CNC output line not found.", {"id": str(output_id)})
            if output.inventory_item_id is None:
                raise ValidationError("Only inventory-linked CNC outputs can be receipted.")
            if output.output_inventory_document_id:
                raise ConflictError("CNC output has already been receipted.")
            if output.completed_quantity <= 0:
                raise ValidationError("Completed quantity is required before receipt.")
            document_id = await self.inventory_document(
                organization_id=work_order.organization_id,
                document_type=InventoryDocumentType.RECEIPT,
                source_warehouse_id=None,
                destination_warehouse_id=work_order.output_warehouse_id,
                item_id=output.inventory_item_id,
                quantity=output.completed_quantity,
                actor_id=actor_id,
                user=user,
                reference=work_order.work_order_number,
                notes="CNC output receipt",
            )
            output.output_inventory_document_id = document_id
            await CncWorkOrderOutputRepository(self.session).update(output)
            await self._sync_production_completion(
                work_order,
                output,
                inventory_document_id=document_id,
                actor_id=actor_id,
            )
            await self.audit(
                action=AuditAction.UPDATE.value,
                entity_type="cnc_output",
                entity_id=output.id,
                actor_id=actor_id,
                after={"inventory_document_id": str(document_id)},
            )
            await self.outbox(
                "cnc.output.received",
                "cnc_work_order",
                work_order.id,
                {"work_order_number": work_order.work_order_number},
            )
            await self.unit_of_work.commit()
            await self.unit_of_work.refresh(output)
            return output
        except Exception:
            await self.unit_of_work.rollback()
            raise

    async def _sync_production_completion(
        self,
        work_order: Any,
        output: Any,
        *,
        inventory_document_id: UUID,
        actor_id: UUID,
    ) -> None:
        if work_order.production_order_id is None or output.inventory_item_id is None:
            return
        order_repository = ProductionOrderRepository(self.session)
        order = await order_repository.get(work_order.production_order_id)
        if order is None:
            return
        if order.product_item_id != output.inventory_item_id:
            raise ValidationError("CNC output item does not match linked production order product.")
        quantity_completed = Decimal(output.completed_quantity)
        quantity_rejected = Decimal(output.rejected_quantity)
        if Decimal(order.completed_quantity) + quantity_completed > Decimal(order.planned_quantity):
            raise ConflictError("CNC receipt exceeds linked production order quantity.")
        completion_repository = ProductionCompletionRepository(self.session)
        await completion_repository.create(
            ProductionCompletionModel(
                production_order_id=order.id,
                completion_number=await completion_repository.next_completion_number(order.id),
                quantity_completed=quantity_completed,
                quantity_rejected=quantity_rejected,
                destination_warehouse_id=work_order.output_warehouse_id,
                destination_location_id=None,
                inventory_document_id=inventory_document_id,
                notes=f"CNC work order {work_order.work_order_number}",
                completed_by_employee_id=work_order.operator_employee_id,
                created_by_user_id=actor_id,
                posted_at=datetime.now(UTC),
            )
        )
        order.completed_quantity = Decimal(order.completed_quantity) + quantity_completed
        order.rejected_quantity = Decimal(order.rejected_quantity) + quantity_rejected
        if order.completed_quantity >= order.planned_quantity:
            order.status = ProductionOrderStatus.COMPLETED.value
            order.completed_at = datetime.now(UTC)
            order.completed_by_user_id = actor_id
            order.actual_end_date = order.completed_at
            order.is_active = False
        else:
            order.status = ProductionOrderStatus.PARTIALLY_COMPLETED.value
        await order_repository.update(order)

    async def register_offcut(
        self, work_order_id: UUID, data: dict[str, Any], *, actor_id: UUID, user: Any | None = None
    ) -> CncOffcutModel:
        work_order = await self.get_work_order(work_order_id)
        await self.ensure_work_order_scope(work_order, user)
        material_item_id = data.get("material_item_id") or work_order.material_item_id
        if material_item_id is None:
            raise ValidationError("Material is required for offcut registration.")
        await self.ensure_item(work_order.organization_id, material_item_id)
        await self.ensure_warehouse(work_order.organization_id, data["warehouse_id"])
        await self.ensure_warehouse_access(user, data["warehouse_id"])
        for field in ("length_mm", "width_mm", "thickness_mm", "quantity"):
            if decimal(data[field]) <= 0:
                raise ValidationError("Offcut dimensions and quantity must be greater than zero.")
        offcut = await CncOffcutRepository(self.session).create(
            CncOffcutModel(
                organization_id=work_order.organization_id,
                source_work_order_id=work_order.id,
                material_item_id=material_item_id,
                offcut_code=data["offcut_code"],
                length_mm=data["length_mm"],
                width_mm=data["width_mm"],
                thickness_mm=data["thickness_mm"],
                quantity=data["quantity"],
                warehouse_id=data["warehouse_id"],
                location_id=data.get("location_id"),
                status=CncOffcutStatus.AVAILABLE.value,
                notes=data.get("notes"),
            )
        )
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_offcut",
            entity_id=offcut.id,
            actor_id=actor_id,
            after={"offcut_code": offcut.offcut_code},
        )
        await self.commit_refresh(offcut)
        return offcut
