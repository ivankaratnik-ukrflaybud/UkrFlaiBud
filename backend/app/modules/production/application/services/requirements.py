from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from app.modules.production.application.services.common import ProductionServiceBase
from app.modules.production.domain.entities import ProductionMaterialSourceType
from app.modules.production.infrastructure.repositories import ProductionRequirementRepository


class RequirementService(ProductionServiceBase):
    async def list_requirements(
        self, order_id: UUID, *, user: Any | None = None
    ) -> list[dict[str, Any]]:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        requirements = await ProductionRequirementRepository(self.session).list_for_order(order_id)
        availability = []
        for requirement in requirements:
            physical = Decimal("0")
            reserved_elsewhere = Decimal("0")
            if (
                requirement.inventory_item_id
                and requirement.source_type != ProductionMaterialSourceType.MANUAL.value
            ):
                physical = await self.stock_quantity(
                    order.organization_id,
                    requirement.inventory_item_id,
                    order.material_warehouse_id,
                )
                reserved_elsewhere = await self.reserved_by_others(
                    requirement.inventory_item_id,
                    order.material_warehouse_id,
                    exclude_order_id=order.id,
                )
            available = max(Decimal("0"), physical - reserved_elsewhere)
            remaining_to_issue = max(
                Decimal("0"),
                Decimal(requirement.planned_quantity)
                - Decimal(requirement.issued_quantity)
                + Decimal(requirement.returned_quantity),
            )
            shortage = max(Decimal("0"), Decimal(requirement.planned_quantity) - available)
            availability.append(
                {
                    "id": requirement.id,
                    "line_number": requirement.line_number,
                    "inventory_item_id": requirement.inventory_item_id,
                    "item_code_snapshot": requirement.item_code_snapshot,
                    "display_name": requirement.display_name,
                    "planned_quantity": requirement.planned_quantity,
                    "reserved_quantity": requirement.reserved_quantity,
                    "issued_quantity": requirement.issued_quantity,
                    "returned_quantity": requirement.returned_quantity,
                    "consumed_quantity": requirement.consumed_quantity,
                    "scrapped_quantity": requirement.scrapped_quantity,
                    "unit_name_snapshot": requirement.unit_name_snapshot,
                    "unit_symbol_snapshot": requirement.unit_symbol_snapshot,
                    "source_type": requirement.source_type,
                    "is_optional": requirement.is_optional,
                    "is_alternative": requirement.is_alternative,
                    "available_quantity": available,
                    "shortage_quantity": shortage,
                    "remaining_to_issue": remaining_to_issue,
                }
            )
        return availability
