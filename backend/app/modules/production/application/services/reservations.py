from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import (
    ProductionMaterialTransactionType,
    ProductionOrderStatus,
)
from app.modules.production.infrastructure.models import ProductionMaterialReservationModel
from app.modules.production.infrastructure.repositories import (
    ProductionOrderRepository,
    ProductionReservationRepository,
)


class ReservationService(ProductionServiceBase):
    async def reserve(
        self,
        order_id: UUID,
        lines: list[dict[str, Any]] | None,
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> list[ProductionMaterialReservationModel]:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        await self.ensure_order_editable(order)
        reservation_lines = lines or [
            {
                "material_requirement_id": requirement.id,
                "quantity": _remaining_to_reserve(requirement),
            }
            for requirement in await self.requirements_for_reservation(order_id)
            if _remaining_to_reserve(requirement) > 0
        ]
        created: list[ProductionMaterialReservationModel] = []
        transaction_lines: list[dict[str, Any]] = []
        repository = ProductionReservationRepository(self.session)
        for line in reservation_lines:
            requirement = await self.get_requirement(
                order_id, line["material_requirement_id"], for_update=True
            )
            quantity = decimal(line["quantity"])
            self.validate_requirement_stock_line(requirement, quantity)
            inventory_item_id = requirement.inventory_item_id
            if inventory_item_id is None:
                raise ConflictError("Requirement is not linked to inventory item.")
            if requirement.is_optional and not line.get("activate_optional"):
                continue
            remaining = _remaining_to_reserve(requirement)
            if quantity > remaining:
                raise ConflictError("Reservation exceeds remaining material requirement.")
            physical = await self.stock_quantity(
                order.organization_id, inventory_item_id, order.material_warehouse_id
            )
            reserved_elsewhere = await self.reserved_by_others(
                inventory_item_id,
                order.material_warehouse_id,
                exclude_order_id=order.id,
            )
            if quantity > physical - reserved_elsewhere:
                raise ConflictError("Insufficient available stock for reservation.")
            reservation = await repository.create(
                ProductionMaterialReservationModel(
                    production_order_id=order.id,
                    material_requirement_id=requirement.id,
                    inventory_item_id=requirement.inventory_item_id,
                    warehouse_id=order.material_warehouse_id,
                    quantity=quantity,
                    created_by_user_id=actor_id,
                )
            )
            requirement.reserved_quantity = Decimal(requirement.reserved_quantity) + quantity
            created.append(reservation)
            transaction_lines.append(
                {
                    "material_requirement_id": requirement.id,
                    "inventory_item_id": inventory_item_id,
                    "warehouse_id": order.material_warehouse_id,
                    "quantity": quantity,
                }
            )
        if created:
            order.status = ProductionOrderStatus.MATERIALS_RESERVED.value
            await ProductionOrderRepository(self.session).update(order)
            await self.create_material_transaction(
                order,
                transaction_type=ProductionMaterialTransactionType.RESERVATION.value,
                lines=transaction_lines,
                actor_id=actor_id,
            )
            await self.audit(
                action=AuditAction.CREATE.value,
                entity_type="production_material_reservation",
                entity_id=order.id,
                actor_id=actor_id,
                after={"lines": len(created)},
            )
        await self.unit_of_work.commit()
        return created

    async def requirements_for_reservation(self, order_id: UUID) -> Any:
        from app.modules.production.infrastructure.repositories import (
            ProductionRequirementRepository,
        )

        return await ProductionRequirementRepository(self.session).list_for_order(order_id)

    async def release_all(self, order_id: UUID, *, actor_id: UUID) -> None:
        order = await self.get_order(order_id)
        reservations = await ProductionReservationRepository(self.session).active_for_order(
            order_id
        )
        if not reservations:
            return
        transaction_lines: list[dict[str, Any]] = []
        for reservation in reservations:
            requirement = await self.get_requirement(
                order_id, reservation.material_requirement_id, for_update=True
            )
            reservation.status = "released"
            reservation.released_at = datetime.now(UTC)
            requirement.reserved_quantity = max(
                Decimal("0"), Decimal(requirement.reserved_quantity) - Decimal(reservation.quantity)
            )
            transaction_lines.append(
                {
                    "material_requirement_id": requirement.id,
                    "inventory_item_id": requirement.inventory_item_id,
                    "warehouse_id": reservation.warehouse_id,
                    "quantity": reservation.quantity,
                }
            )
        await self.create_material_transaction(
            order,
            transaction_type=ProductionMaterialTransactionType.RESERVATION_RELEASE.value,
            lines=transaction_lines,
            actor_id=actor_id,
        )


def _remaining_to_reserve(requirement: Any) -> Decimal:
    if requirement.inventory_item_id is None:
        return Decimal("0")
    if requirement.is_optional:
        return Decimal("0")
    return max(
        Decimal("0"),
        Decimal(requirement.planned_quantity) - Decimal(requirement.reserved_quantity),
    )
