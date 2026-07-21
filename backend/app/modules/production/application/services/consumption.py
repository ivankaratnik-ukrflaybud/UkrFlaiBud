from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.base import ConflictError, ValidationError
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import ProductionMaterialTransactionType


class ConsumptionService(ProductionServiceBase):
    async def record(
        self,
        order_id: UUID,
        lines: list[dict[str, Any]],
        *,
        transaction_type: str,
        actor_id: UUID,
        reason: str | None = None,
    ) -> Any:
        if transaction_type not in {
            ProductionMaterialTransactionType.CONSUMPTION.value,
            ProductionMaterialTransactionType.SCRAP.value,
        }:
            raise ValidationError("Unsupported production consumption transaction.")
        order = await self.get_order(order_id)
        await self.ensure_order_editable(order)
        transaction_lines: list[dict[str, Any]] = []
        for line in lines:
            requirement = await self.get_requirement(
                order.id, line["material_requirement_id"], for_update=True
            )
            quantity = decimal(line["quantity"])
            self.validate_requirement_stock_line(requirement, quantity)
            used = (
                Decimal(requirement.consumed_quantity)
                + Decimal(requirement.scrapped_quantity)
                + Decimal(requirement.returned_quantity)
                + quantity
            )
            if used > Decimal(requirement.issued_quantity):
                raise ConflictError(
                    "Consumed, returned and scrapped quantity exceeds issued quantity."
                )
            if transaction_type == ProductionMaterialTransactionType.CONSUMPTION.value:
                requirement.consumed_quantity = Decimal(requirement.consumed_quantity) + quantity
            else:
                requirement.scrapped_quantity = Decimal(requirement.scrapped_quantity) + quantity
            transaction_lines.append(
                {
                    "material_requirement_id": requirement.id,
                    "inventory_item_id": requirement.inventory_item_id,
                    "warehouse_id": order.material_warehouse_id,
                    "quantity": quantity,
                }
            )
        transaction = await self.create_material_transaction(
            order,
            transaction_type=transaction_type,
            lines=transaction_lines,
            actor_id=actor_id,
            reason=reason,
        )
        await self.unit_of_work.commit()
        return transaction
