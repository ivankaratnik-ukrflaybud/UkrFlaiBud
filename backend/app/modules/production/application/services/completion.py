from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.base import ConflictError, ValidationError
from app.modules.inventory.application.services import DocumentService
from app.modules.inventory.domain.entities import InventoryDocumentType
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import ProductionOrderStatus
from app.modules.production.infrastructure.models import (
    ProductionCompletionModel,
    ProductionOutputSerialModel,
)
from app.modules.production.infrastructure.repositories import (
    ProductionCompletionRepository,
    ProductionOrderRepository,
    ProductionOutputSerialRepository,
)


class CompletionService(ProductionServiceBase):
    async def complete(
        self,
        order_id: UUID,
        data: dict[str, Any],
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> ProductionCompletionModel:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        await self.ensure_order_editable(order)
        quantity_completed = decimal(data["quantity_completed"])
        quantity_rejected = decimal(data.get("quantity_rejected", 0))
        if quantity_completed <= 0:
            raise ValidationError("Completed quantity must be greater than zero.")
        if quantity_rejected < 0:
            raise ValidationError("Rejected quantity cannot be negative.")
        if Decimal(order.completed_quantity) + quantity_completed > Decimal(order.planned_quantity):
            raise ConflictError("Completion exceeds planned production quantity.")
        destination_warehouse_id = (
            data.get("destination_warehouse_id") or order.finished_goods_warehouse_id
        )
        await self.ensure_warehouse_access(user, destination_warehouse_id)
        serials = await self.ensure_output_serials(
            order, data.get("serial_numbers") or [], quantity_completed
        )
        inventory_document = await DocumentService(self.unit_of_work).create_draft(
            {
                "organization_id": order.organization_id,
                "document_type": InventoryDocumentType.RECEIPT.value,
                "destination_warehouse_id": destination_warehouse_id,
                "responsible_employee_id": order.responsible_employee_id,
                "reference": order.order_number,
                "notes": data.get("notes"),
            },
            actor_id=actor_id,
        )
        await DocumentService(self.unit_of_work).add_line(
            inventory_document.id,
            {
                "line_number": 1,
                "item_id": order.product_item_id,
                "quantity": quantity_completed,
                "destination_location_id": data.get("destination_location_id"),
                "notes": data.get("notes"),
            },
            actor_id=actor_id,
        )
        await DocumentService(self.unit_of_work).post(
            inventory_document.id, actor_id=actor_id, user=user
        )
        completion_repository = ProductionCompletionRepository(self.session)
        completion = await completion_repository.create(
            ProductionCompletionModel(
                production_order_id=order.id,
                completion_number=await completion_repository.next_completion_number(order.id),
                quantity_completed=quantity_completed,
                quantity_rejected=quantity_rejected,
                destination_warehouse_id=destination_warehouse_id,
                destination_location_id=data.get("destination_location_id"),
                inventory_document_id=inventory_document.id,
                notes=data.get("notes"),
                completed_by_employee_id=data.get("completed_by_employee_id"),
                created_by_user_id=actor_id,
                posted_at=datetime.now(UTC),
            )
        )
        output_repository = ProductionOutputSerialRepository(self.session)
        for serial in serials:
            if await output_repository.exists_by_serial_number(serial.serial_number):
                raise ConflictError("Serial number is already registered as production output.")
            await output_repository.create(
                ProductionOutputSerialModel(
                    production_order_id=order.id,
                    completion_id=completion.id,
                    inventory_serial_id=serial.id,
                    product_item_id=order.product_item_id,
                    serial_number_snapshot=serial.serial_number,
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
        await ProductionOrderRepository(self.session).update(order)
        await self.outbox(
            "production.output.received",
            "production_order",
            order.id,
            {"order_number": order.order_number, "quantity_completed": str(quantity_completed)},
        )
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(completion)
        return completion
