from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.bom.domain.entities import BomLineSourceType
from app.modules.inventory.infrastructure.models import ItemModel, UnitOfMeasureModel
from app.modules.production.application.services.common import ProductionServiceBase, decimal
from app.modules.production.domain.entities import (
    ProductionMaterialSourceType,
    ProductionOrderStatus,
)
from app.modules.production.infrastructure.models import (
    ProductionMaterialRequirementModel,
    ProductionOrderBomSnapshotModel,
    ProductionOrderModel,
)
from app.modules.production.infrastructure.repositories import (
    ProductionOrderRepository,
    ProductionRequirementRepository,
    ProductionSnapshotRepository,
)
from app.schemas.pagination import PageRequest, SortDirection

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"planned", "cancelled"},
    "planned": {"released", "cancelled"},
    "released": {"materials_reserved", "in_progress", "suspended"},
    "materials_reserved": {"in_progress", "suspended"},
    "in_progress": {"partially_completed", "completed", "suspended"},
    "partially_completed": {"in_progress", "completed", "suspended"},
    "suspended": {"released", "in_progress", "cancelled"},
}


class ProductionOrderService(ProductionServiceBase):
    async def create_order(
        self, data: dict[str, Any], *, actor_id: UUID, user: Any | None = None
    ) -> ProductionOrderModel:
        planned_quantity = decimal(data["planned_quantity"])
        if planned_quantity <= 0:
            raise ValidationError("Planned quantity must be greater than zero.")
        organization_id = data["organization_id"]
        product = await self.ensure_item(organization_id, data["product_item_id"])
        bom, version = await self.get_approved_bom(organization_id, data["bom_version_id"])
        if bom.product_item_id and bom.product_item_id != product.id:
            raise ValidationError("Selected BOM does not belong to the selected product.")
        unit = await self.ensure_unit(
            organization_id, data.get("unit_of_measure_id") or product.unit_of_measure_id
        )
        await self.ensure_site(organization_id, data["site_id"])
        material_warehouse = await self.ensure_warehouse(
            organization_id, data["material_warehouse_id"], site_id=data["site_id"]
        )
        finished_warehouse = await self.ensure_warehouse(
            organization_id, data["finished_goods_warehouse_id"], site_id=data["site_id"]
        )
        if data.get("production_warehouse_id"):
            await self.ensure_warehouse(
                organization_id, data["production_warehouse_id"], site_id=data["site_id"]
            )
        await self.ensure_department(organization_id, data.get("department_id"))
        await self.ensure_employee(organization_id, data.get("responsible_employee_id"))
        await self.ensure_employee(organization_id, data.get("production_manager_employee_id"))
        await self.ensure_warehouse_access(
            user,
            data.get("production_warehouse_id"),
            material_warehouse.id,
            finished_warehouse.id,
        )
        await self.ensure_site_access(user, data["site_id"])
        repository = ProductionOrderRepository(self.session)
        order_number = data.get("order_number") or await self.next_order_number(organization_id)
        if await repository.exists_by_number(organization_id, order_number):
            raise ConflictError("Production order number must be unique.")
        order = await repository.create(
            ProductionOrderModel(
                organization_id=organization_id,
                order_number=order_number,
                name=data.get("name") or f"{order_number} - {product.name}",
                product_item_id=product.id,
                bom_id=bom.id,
                bom_version_id=version.id,
                bom_version_number=version.version_number,
                order_type=data.get("order_type", "standard"),
                status=data.get("status", ProductionOrderStatus.DRAFT.value),
                priority=data.get("priority", "normal"),
                site_id=data["site_id"],
                department_id=data.get("department_id"),
                production_warehouse_id=data.get("production_warehouse_id"),
                material_warehouse_id=material_warehouse.id,
                finished_goods_warehouse_id=finished_warehouse.id,
                planned_quantity=planned_quantity,
                unit_of_measure_id=unit.id,
                planned_start_date=data.get("planned_start_date"),
                planned_end_date=data.get("planned_end_date"),
                responsible_employee_id=data.get("responsible_employee_id"),
                production_manager_employee_id=data.get("production_manager_employee_id"),
                notes=data.get("notes"),
                created_by_user_id=actor_id,
            )
        )
        await self.create_snapshot_and_requirements(order, product, unit, actor_id=actor_id)
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="production_order",
            entity_id=order.id,
            actor_id=actor_id,
            after={"order_number": order.order_number, "status": order.status},
        )
        await self.outbox(
            "production.order.created",
            "production_order",
            order.id,
            {"order_number": order.order_number},
        )
        await self.commit_refresh(order)
        return order

    async def list_orders(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: Any | None = None,
    ) -> tuple[list[ProductionOrderModel], int]:
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
        return await ProductionOrderRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, order_id: UUID, *, user: Any | None = None) -> ProductionOrderModel:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        return order

    async def update_order(
        self,
        order_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
        user: Any | None = None,
    ) -> ProductionOrderModel:
        order = await self.get(order_id, user=user)
        await self.ensure_order_editable(order)
        if expected_version is not None and order.version != expected_version:
            raise ConflictError("Entity version conflict.")
        locked_fields = {"product_item_id", "bom_version_id", "planned_quantity"}
        if order.status not in {
            ProductionOrderStatus.DRAFT.value,
            ProductionOrderStatus.PLANNED.value,
        }:
            if locked_fields & data.keys():
                raise ConflictError("Released orders require controlled revision for core fields.")
        before = {"status": order.status, "planned_quantity": str(order.planned_quantity)}
        for field, value in data.items():
            setattr(order, field, value)
        await ProductionOrderRepository(self.session).update(order)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="production_order",
            entity_id=order.id,
            actor_id=actor_id,
            before=before,
            after={"status": order.status, "planned_quantity": str(order.planned_quantity)},
        )
        await self.commit_refresh(order)
        return order

    async def transition(
        self,
        order_id: UUID,
        target_status: str,
        *,
        actor_id: UUID,
        user: Any | None = None,
        reason: str | None = None,
    ) -> ProductionOrderModel:
        order = await self.get(order_id, user=user)
        await self.ensure_order_editable(order)
        source_status = order.status
        if target_status not in ALLOWED_TRANSITIONS.get(source_status, set()):
            raise ConflictError("Invalid production order status transition.")
        if target_status == ProductionOrderStatus.CANCELLED.value and not reason:
            raise ValidationError("Cancellation reason is required.")
        if target_status == ProductionOrderStatus.SUSPENDED.value and not reason:
            raise ValidationError("Suspension reason is required.")
        now = datetime.now(UTC)
        order.status = target_status
        if target_status == ProductionOrderStatus.RELEASED.value:
            order.released_at = order.released_at or now
            order.released_by_user_id = order.released_by_user_id or actor_id
        if (
            target_status == ProductionOrderStatus.IN_PROGRESS.value
            and order.actual_start_date is None
        ):
            order.actual_start_date = now
        if target_status == ProductionOrderStatus.COMPLETED.value:
            order.completed_at = now
            order.completed_by_user_id = actor_id
            order.actual_end_date = now
            order.is_active = False
        if target_status == ProductionOrderStatus.CANCELLED.value:
            order.cancelled_at = now
            order.cancelled_by_user_id = actor_id
            order.cancellation_reason = reason
            order.is_active = False
            from app.modules.production.application.services.reservations import ReservationService

            await ReservationService(self.unit_of_work).release_all(order.id, actor_id=actor_id)
        if target_status == ProductionOrderStatus.SUSPENDED.value:
            order.suspension_reason = reason
        await ProductionOrderRepository(self.session).update(order)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="production_order",
            entity_id=order.id,
            actor_id=actor_id,
            before={"status": source_status},
            after={"status": target_status, "reason": reason},
        )
        await self.outbox(
            f"production.order.{_event_suffix(target_status)}",
            "production_order",
            order.id,
            {"order_number": order.order_number, "status": order.status},
        )
        await self.commit_refresh(order)
        return order

    async def create_snapshot_and_requirements(
        self,
        order: ProductionOrderModel,
        product: ItemModel,
        unit: UnitOfMeasureModel,
        *,
        actor_id: UUID,
    ) -> None:
        bom, version = await self.get_approved_bom(order.organization_id, order.bom_version_id)
        lines = await self.bom_lines(version.id)
        snapshot_json = version.snapshot_data or {
            "specification": {"code": bom.code, "name": bom.name},
            "version": {
                "version_number": version.version_number,
                "approved_at": version.approved_at.isoformat() if version.approved_at else None,
            },
            "lines": [],
        }
        await ProductionSnapshotRepository(self.session).create(
            ProductionOrderBomSnapshotModel(
                production_order_id=order.id,
                source_bom_id=bom.id,
                source_bom_version_id=version.id,
                source_bom_version_number=version.version_number,
                specification_code=bom.code,
                specification_name=bom.name,
                product_code=product.sku,
                product_name=product.name,
                unit_name=unit.name,
                unit_symbol=unit.symbol,
                approved_at=version.approved_at,
                snapshot_json=snapshot_json,
            )
        )
        requirement_repository = ProductionRequirementRepository(self.session)
        for line in lines:
            line_unit = await self.session.get(UnitOfMeasureModel, line.unit_of_measure_id)
            item = (
                await self.session.get(ItemModel, line.inventory_item_id)
                if line.inventory_item_id
                else None
            )
            quantity_per_unit = Decimal(line.quantity)
            planned = quantity_per_unit * Decimal(order.planned_quantity)
            planned_with_waste = planned * (
                Decimal("1") + Decimal(line.waste_percentage) / Decimal("100")
            )
            source_type = _source_type(line.source_type)
            await requirement_repository.create(
                ProductionMaterialRequirementModel(
                    production_order_id=order.id,
                    source_bom_line_id=line.id,
                    line_number=line.line_number,
                    parent_requirement_id=None,
                    inventory_item_id=(
                        line.inventory_item_id
                        if source_type != ProductionMaterialSourceType.MANUAL.value
                        else None
                    ),
                    item_code_snapshot=line.position_code or (item.sku if item else None),
                    display_name=line.display_name,
                    description=line.description,
                    required_quantity_per_unit=quantity_per_unit,
                    waste_percentage=line.waste_percentage,
                    planned_quantity=planned_with_waste,
                    unit_of_measure_id=line.unit_of_measure_id,
                    unit_name_snapshot=line_unit.name if line_unit else "",
                    unit_symbol_snapshot=line_unit.symbol if line_unit else "",
                    is_optional=line.is_optional,
                    is_alternative=line.is_alternative,
                    alternative_group=line.alternative_group,
                    source_type=source_type,
                    technical_requirements=line.technical_requirements,
                    notes=line.notes,
                    sort_order=line.sort_order,
                )
            )
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="production_order_bom_snapshot",
            entity_id=order.id,
            actor_id=actor_id,
            after={"requirements": len(lines), "bom_version_id": str(version.id)},
        )

    async def next_order_number(self, organization_id: UUID) -> str:
        sequence = await ProductionOrderRepository(self.session).next_sequence(organization_id)
        return f"PO-{datetime.now(UTC):%Y%m%d}-{sequence:05d}"


def _source_type(source_type: str) -> str:
    if source_type == BomLineSourceType.INVENTORY_ITEM.value:
        return ProductionMaterialSourceType.INVENTORY_ITEM.value
    if source_type == BomLineSourceType.SUBASSEMBLY.value:
        return ProductionMaterialSourceType.SUBASSEMBLY.value
    return ProductionMaterialSourceType.MANUAL.value


def _event_suffix(status: str) -> str:
    if status == ProductionOrderStatus.RELEASED.value:
        return "released"
    if status == ProductionOrderStatus.IN_PROGRESS.value:
        return "started"
    if status == ProductionOrderStatus.SUSPENDED.value:
        return "suspended"
    if status == ProductionOrderStatus.COMPLETED.value:
        return "completed"
    if status == ProductionOrderStatus.CANCELLED.value:
        return "cancelled"
    return "updated"
