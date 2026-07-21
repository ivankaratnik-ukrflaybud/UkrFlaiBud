from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.base import ConflictError
from app.modules.inventory.domain.entities import InventoryDocumentType
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import ProductionMaterialTransactionType


class MaterialReturnService(ProductionServiceBase):
    async def return_materials(
        self,
        order_id: UUID,
        lines: list[dict[str, Any]],
        *,
        actor_id: UUID,
        user: Any | None = None,
        notes: str | None = None,
    ) -> Any:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        await self.ensure_order_editable(order)
        document_lines: list[dict[str, Any]] = []
        transaction_lines: list[dict[str, Any]] = []
        for line in lines:
            requirement = await self.get_requirement(
                order.id, line["material_requirement_id"], for_update=True
            )
            quantity = decimal(line["quantity"])
            self.validate_requirement_stock_line(requirement, quantity)
            returnable = Decimal(requirement.issued_quantity) - Decimal(
                requirement.returned_quantity
            )
            if quantity > returnable:
                raise ConflictError("Return quantity exceeds issued unused material.")
            requirement.returned_quantity = Decimal(requirement.returned_quantity) + quantity
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
            document_type=InventoryDocumentType.RETURN_IN,
            actor_id=actor_id,
            user=user,
            reference=order.order_number,
            notes=notes,
        )
        transaction = await self.create_material_transaction(
            order,
            transaction_type=ProductionMaterialTransactionType.RETURN.value,
            inventory_document_id=document_id,
            lines=transaction_lines,
            actor_id=actor_id,
            notes=notes,
        )
        await self.unit_of_work.commit()
        return transaction
