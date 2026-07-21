from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.base import ConflictError, ValidationError
from app.modules.inventory.domain.entities import InventoryDocumentType
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import (
    ProductionMaterialTransactionType,
    ProductionOrderStatus,
)
from app.modules.production.infrastructure.repositories import ProductionOrderRepository


class MaterialIssueService(ProductionServiceBase):
    async def issue(
        self,
        order_id: UUID,
        lines: list[dict[str, Any]],
        *,
        actor_id: UUID,
        user: Any | None = None,
        allow_overissue: bool = False,
        reason: str | None = None,
        notes: str | None = None,
    ) -> Any:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        await self.ensure_order_editable(order)
        if allow_overissue and not reason:
            raise ValidationError("Overissue reason is required.")
        document_lines: list[dict[str, Any]] = []
        transaction_lines: list[dict[str, Any]] = []
        for line in lines:
            requirement = await self.get_requirement(
                order.id, line["material_requirement_id"], for_update=True
            )
            quantity = decimal(line["quantity"])
            self.validate_requirement_stock_line(requirement, quantity)
            remaining = (
                Decimal(requirement.planned_quantity)
                - Decimal(requirement.issued_quantity)
                + Decimal(requirement.returned_quantity)
            )
            if quantity > remaining and not allow_overissue:
                raise ConflictError("Material issue exceeds remaining requirement.")
            requirement.issued_quantity = Decimal(requirement.issued_quantity) + quantity
            if requirement.reserved_quantity:
                requirement.reserved_quantity = max(
                    Decimal("0"), Decimal(requirement.reserved_quantity) - quantity
                )
            document_lines.append(
                {
                    "material_requirement_id": requirement.id,
                    "inventory_item_id": requirement.inventory_item_id,
                    "quantity": quantity,
                    "location_id": line.get("location_id"),
                    "lot_id": line.get("lot_id"),
                    "notes": line.get("notes"),
                }
            )
            transaction_lines.append(
                {
                    "material_requirement_id": requirement.id,
                    "inventory_item_id": requirement.inventory_item_id,
                    "warehouse_id": order.material_warehouse_id,
                    "location_id": line.get("location_id"),
                    "lot_id": line.get("lot_id"),
                    "serial_id": line.get("serial_id"),
                    "quantity": quantity,
                }
            )
        document_id = await self.issue_or_return_document(
            order,
            document_lines,
            document_type=InventoryDocumentType.ISSUE,
            actor_id=actor_id,
            user=user,
            reference=order.order_number,
            notes=notes,
        )
        transaction = await self.create_material_transaction(
            order,
            transaction_type=ProductionMaterialTransactionType.ISSUE.value,
            inventory_document_id=document_id,
            lines=transaction_lines,
            actor_id=actor_id,
            reason=reason,
            notes=notes,
        )
        if order.status in {
            ProductionOrderStatus.RELEASED.value,
            ProductionOrderStatus.MATERIALS_RESERVED.value,
        }:
            order.status = ProductionOrderStatus.IN_PROGRESS.value
            await ProductionOrderRepository(self.session).update(order)
        await self.outbox(
            "production.material.issued",
            "production_order",
            order.id,
            {"order_number": order.order_number, "document_id": str(document_id)},
        )
        await self.unit_of_work.commit()
        return transaction
