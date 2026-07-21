from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.modules.production.application.services.common import ProductionServiceBase
from app.modules.production.infrastructure.models import (
    ProductionMaterialRequirementModel,
    ProductionOrderModel,
)


class ProductionQueryService(ProductionServiceBase):
    async def dashboard(self, organization_id: UUID, *, user: Any | None = None) -> dict[str, Any]:
        statement = select(ProductionOrderModel).where(
            ProductionOrderModel.organization_id == organization_id,
            ProductionOrderModel.deleted_at.is_(None),
        )
        if user and not getattr(user, "is_superuser", False):
            from app.modules.inventory.application.services import InventoryScopeService

            scope = InventoryScopeService(self.unit_of_work)
            site_ids = await scope.accessible_site_ids(user)
            warehouse_ids = await scope.accessible_warehouse_ids(user)
            if not site_ids and not warehouse_ids:
                return _empty_dashboard()
            if site_ids:
                statement = statement.where(ProductionOrderModel.site_id.in_(site_ids))
            if warehouse_ids:
                statement = statement.where(
                    ProductionOrderModel.material_warehouse_id.in_(warehouse_ids)
                )
        orders = list((await self.session.scalars(statement)).all())
        today = datetime.now(UTC).date()
        shortage_order_ids = await self._shortage_order_ids(organization_id)
        return {
            "active_orders": len(
                [order for order in orders if order.status not in {"completed", "cancelled"}]
            ),
            "planned": len([order for order in orders if order.status == "planned"]),
            "in_progress": len([order for order in orders if order.status == "in_progress"]),
            "partially_completed": len(
                [order for order in orders if order.status == "partially_completed"]
            ),
            "overdue": len(
                [
                    order
                    for order in orders
                    if order.planned_end_date
                    and order.planned_end_date.date() < today
                    and order.status not in {"completed", "cancelled"}
                ]
            ),
            "with_material_shortage": len({order.id for order in orders} & shortage_order_ids),
            "completed_today": len(
                [
                    order
                    for order in orders
                    if order.completed_at and order.completed_at.date() == today
                ]
            ),
            "urgent_orders": [
                _order_summary(order) for order in orders if order.priority == "urgent"
            ][:10],
            "active_order_rows": [
                _order_summary(order)
                for order in orders
                if order.status not in {"completed", "cancelled"}
            ][:20],
        }

    async def _shortage_order_ids(self, organization_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(
                ProductionMaterialRequirementModel.production_order_id,
                ProductionMaterialRequirementModel.planned_quantity,
                ProductionMaterialRequirementModel.inventory_item_id,
                ProductionOrderModel.material_warehouse_id,
            )
            .join(
                ProductionOrderModel,
                ProductionOrderModel.id == ProductionMaterialRequirementModel.production_order_id,
            )
            .where(
                ProductionOrderModel.organization_id == organization_id,
                ProductionMaterialRequirementModel.inventory_item_id.is_not(None),
            )
        )
        shortages: set[UUID] = set()
        for row in result:
            stock = await self.stock_quantity(
                organization_id, row.inventory_item_id, row.material_warehouse_id
            )
            if Decimal(row.planned_quantity) > stock:
                shortages.add(row.production_order_id)
        return shortages


def _empty_dashboard() -> dict[str, Any]:
    return {
        "active_orders": 0,
        "planned": 0,
        "in_progress": 0,
        "partially_completed": 0,
        "overdue": 0,
        "with_material_shortage": 0,
        "completed_today": 0,
        "urgent_orders": [],
        "active_order_rows": [],
    }


def _order_summary(order: ProductionOrderModel) -> dict[str, Any]:
    return {
        "id": order.id,
        "order_number": order.order_number,
        "name": order.name,
        "status": order.status,
        "priority": order.priority,
        "planned_quantity": order.planned_quantity,
        "completed_quantity": order.completed_quantity,
        "planned_end_date": order.planned_end_date,
    }
