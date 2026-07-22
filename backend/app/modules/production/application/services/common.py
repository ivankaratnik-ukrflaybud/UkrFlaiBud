from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditLog
from app.database.outbox import OutboxEvent
from app.models.base import (
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.bom.domain.entities import BomVersionStatus
from app.modules.bom.infrastructure.models import (
    BomLineModel,
    BomSpecificationModel,
    BomVersionModel,
)
from app.modules.inventory.application.services import DocumentService, InventoryScopeService
from app.modules.inventory.domain.entities import InventoryDocumentType, ItemType, SerialStatus
from app.modules.inventory.infrastructure.models import (
    InventorySerialModel,
    ItemModel,
    SiteModel,
    StockBalanceModel,
    UnitOfMeasureModel,
    WarehouseModel,
)
from app.modules.organizations.infrastructure.models import DepartmentModel, EmployeeModel
from app.modules.production.domain.entities import (
    ProductionMaterialSourceType,
    ProductionMaterialTransactionStatus,
    ProductionOrderStatus,
)
from app.modules.production.infrastructure.models import (
    ProductionMaterialRequirementModel,
    ProductionMaterialTransactionLineModel,
    ProductionMaterialTransactionModel,
    ProductionOrderModel,
)
from app.modules.production.infrastructure.repositories import (
    ProductionOrderRepository,
    ProductionRequirementRepository,
    ProductionReservationRepository,
    ProductionTransactionLineRepository,
    ProductionTransactionRepository,
)
from app.repositories.sqlalchemy_audit import SQLAlchemyAuditLogRepository
from app.repositories.sqlalchemy_outbox import SQLAlchemyOutboxRepository
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

FINAL_ORDER_STATUSES = {
    ProductionOrderStatus.COMPLETED.value,
    ProductionOrderStatus.CANCELLED.value,
}


class ProductionServiceBase:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def get_order(self, order_id: UUID) -> ProductionOrderModel:
        order = await ProductionOrderRepository(self.session).get(order_id)
        if order is None:
            raise EntityNotFoundError("Production order not found.", {"id": str(order_id)})
        return order

    async def ensure_order_editable(self, order: ProductionOrderModel) -> None:
        if order.status in FINAL_ORDER_STATUSES:
            raise ConflictError("Completed and cancelled production orders are read-only.")

    async def ensure_warehouse_access(self, user: Any | None, *warehouse_ids: UUID | None) -> None:
        if user is None or getattr(user, "is_superuser", False):
            return
        scope = InventoryScopeService(self.unit_of_work)
        for warehouse_id in warehouse_ids:
            if warehouse_id is not None:
                await scope.ensure_warehouse_access(user, warehouse_id)

    async def ensure_site_access(self, user: Any | None, site_id: UUID) -> None:
        if user is None or getattr(user, "is_superuser", False):
            return
        allowed = await InventoryScopeService(self.unit_of_work).accessible_site_ids(user)
        if site_id not in (allowed or set()):
            raise PermissionDeniedError("You do not have access to this site.")

    async def ensure_order_scope(self, order: ProductionOrderModel, user: Any | None) -> None:
        await self.ensure_site_access(user, order.site_id)
        await self.ensure_warehouse_access(
            user,
            order.production_warehouse_id,
            order.material_warehouse_id,
            order.finished_goods_warehouse_id,
        )

    async def ensure_organization(self, organization_id: UUID) -> None:
        exists = await self.session.scalar(
            select(func.count())
            .select_from(BomSpecificationModel)
            .where(BomSpecificationModel.organization_id == organization_id)
        )
        if exists is None:
            return

    async def ensure_item(self, organization_id: UUID, item_id: UUID) -> ItemModel:
        item = await self.session.get(ItemModel, item_id)
        if item is None or item.deleted_at is not None:
            raise EntityNotFoundError("Inventory item not found.", {"id": str(item_id)})
        if item.organization_id != organization_id:
            raise ValidationError("Inventory item must belong to the same organization.")
        if item.item_type == ItemType.SERVICE.value:
            raise ValidationError("Service items cannot be production output.")
        if not item.is_active:
            raise ValidationError("Inactive item cannot be used in production.")
        return item

    async def ensure_unit(self, organization_id: UUID, unit_id: UUID) -> UnitOfMeasureModel:
        unit = await self.session.get(UnitOfMeasureModel, unit_id)
        if unit is None or unit.deleted_at is not None:
            raise EntityNotFoundError("Unit of measure not found.", {"id": str(unit_id)})
        if unit.organization_id != organization_id:
            raise ValidationError("Unit must belong to the same organization.")
        return unit

    async def ensure_site(self, organization_id: UUID, site_id: UUID) -> SiteModel:
        site = await self.session.get(SiteModel, site_id)
        if site is None or site.deleted_at is not None:
            raise EntityNotFoundError("Site not found.", {"id": str(site_id)})
        if site.organization_id != organization_id:
            raise ValidationError("Site must belong to the same organization.")
        if not site.is_active:
            raise ValidationError("Inactive site cannot receive production orders.")
        return site

    async def ensure_warehouse(
        self, organization_id: UUID, warehouse_id: UUID, *, site_id: UUID | None = None
    ) -> WarehouseModel:
        warehouse = await self.session.get(WarehouseModel, warehouse_id)
        if warehouse is None or warehouse.deleted_at is not None:
            raise EntityNotFoundError("Warehouse not found.", {"id": str(warehouse_id)})
        if warehouse.organization_id != organization_id:
            raise ValidationError("Warehouse must belong to the same organization.")
        if site_id is not None and warehouse.site_id != site_id:
            raise ValidationError("Warehouse must belong to the selected site.")
        if not warehouse.is_active:
            raise ValidationError("Inactive warehouse cannot be used in production.")
        return warehouse

    async def ensure_employee(self, organization_id: UUID, employee_id: UUID | None) -> None:
        if employee_id is None:
            return
        employee = await self.session.get(EmployeeModel, employee_id)
        if employee is None or employee.deleted_at is not None:
            raise EntityNotFoundError("Employee not found.", {"id": str(employee_id)})
        if employee.organization_id != organization_id:
            raise ValidationError("Employee must belong to the same organization.")

    async def ensure_department(self, organization_id: UUID, department_id: UUID | None) -> None:
        if department_id is None:
            return
        department = await self.session.get(DepartmentModel, department_id)
        if department is None or department.deleted_at is not None:
            raise EntityNotFoundError("Department not found.", {"id": str(department_id)})
        if department.organization_id != organization_id:
            raise ValidationError("Department must belong to the same organization.")

    async def get_approved_bom(
        self, organization_id: UUID, bom_version_id: UUID
    ) -> tuple[BomSpecificationModel, BomVersionModel]:
        version = await self.session.get(BomVersionModel, bom_version_id)
        if version is None:
            raise EntityNotFoundError("BOM version not found.", {"id": str(bom_version_id)})
        if version.status != BomVersionStatus.APPROVED.value:
            raise ValidationError("Production order requires an approved BOM version.")
        bom = await self.session.get(BomSpecificationModel, version.bom_id)
        if bom is None or bom.deleted_at is not None:
            raise EntityNotFoundError("BOM specification not found.")
        if bom.organization_id != organization_id:
            raise ValidationError("BOM must belong to the same organization.")
        return bom, version

    async def bom_lines(self, version_id: UUID) -> list[BomLineModel]:
        result = await self.session.scalars(
            select(BomLineModel)
            .where(BomLineModel.bom_version_id == version_id)
            .order_by(BomLineModel.sort_order.asc(), BomLineModel.line_number.asc())
        )
        return list(result.all())

    async def stock_quantity(
        self, organization_id: UUID, item_id: UUID, warehouse_id: UUID
    ) -> Decimal:
        quantity = await self.session.scalar(
            select(func.coalesce(func.sum(StockBalanceModel.quantity), 0)).where(
                StockBalanceModel.organization_id == organization_id,
                StockBalanceModel.item_id == item_id,
                StockBalanceModel.warehouse_id == warehouse_id,
            )
        )
        return Decimal(str(quantity or 0))

    async def reserved_by_others(
        self, item_id: UUID, warehouse_id: UUID, *, exclude_order_id: UUID
    ) -> Decimal:
        quantity = await ProductionReservationRepository(self.session).active_quantity_for_item(
            item_id, warehouse_id, exclude_order_id=exclude_order_id
        )
        return Decimal(str(quantity or 0))

    async def issue_or_return_document(
        self,
        order: ProductionOrderModel,
        lines: list[dict[str, Any]],
        *,
        document_type: InventoryDocumentType,
        actor_id: UUID,
        user: Any | None,
        reference: str,
        notes: str | None = None,
    ) -> UUID:
        service = DocumentService(self.unit_of_work)
        document = await service.create_draft(
            {
                "organization_id": order.organization_id,
                "document_type": document_type.value,
                "source_warehouse_id": (
                    order.material_warehouse_id
                    if document_type == InventoryDocumentType.ISSUE
                    else None
                ),
                "destination_warehouse_id": (
                    order.material_warehouse_id
                    if document_type == InventoryDocumentType.RETURN_IN
                    else None
                ),
                "responsible_employee_id": order.responsible_employee_id,
                "reference": reference,
                "notes": notes,
            },
            actor_id=actor_id,
        )
        for index, line in enumerate(lines, start=1):
            await service.add_line(
                document.id,
                {
                    "line_number": index,
                    "item_id": line["inventory_item_id"],
                    "quantity": line["quantity"],
                    "source_location_id": line.get("location_id"),
                    "destination_location_id": line.get("location_id"),
                    "lot_id": line.get("lot_id"),
                    "notes": line.get("notes"),
                },
                actor_id=actor_id,
            )
        await service.post(document.id, actor_id=actor_id, user=user)
        return document.id

    async def create_material_transaction(
        self,
        order: ProductionOrderModel,
        *,
        transaction_type: str,
        lines: list[dict[str, Any]],
        actor_id: UUID,
        inventory_document_id: UUID | None = None,
        reason: str | None = None,
        notes: str | None = None,
    ) -> ProductionMaterialTransactionModel:
        transaction = await ProductionTransactionRepository(self.session).create(
            ProductionMaterialTransactionModel(
                production_order_id=order.id,
                transaction_type=transaction_type,
                inventory_document_id=inventory_document_id,
                status=ProductionMaterialTransactionStatus.POSTED.value,
                notes=notes,
                reason=reason,
                created_by_user_id=actor_id,
                posted_by_user_id=actor_id,
                posted_at=datetime.now(UTC),
            )
        )
        line_repository = ProductionTransactionLineRepository(self.session)
        for line in lines:
            await line_repository.create(
                ProductionMaterialTransactionLineModel(
                    transaction_id=transaction.id,
                    material_requirement_id=line["material_requirement_id"],
                    inventory_item_id=line["inventory_item_id"],
                    warehouse_id=line["warehouse_id"],
                    location_id=line.get("location_id"),
                    lot_id=line.get("lot_id"),
                    serial_id=line.get("serial_id"),
                    quantity=line["quantity"],
                )
            )
        return transaction

    async def get_requirement(
        self, order_id: UUID, requirement_id: UUID, *, for_update: bool = False
    ) -> ProductionMaterialRequirementModel:
        requirement = await ProductionRequirementRepository(self.session).get_for_order(
            order_id, requirement_id, for_update=for_update
        )
        if requirement is None:
            raise EntityNotFoundError(
                "Production material requirement not found.", {"id": str(requirement_id)}
            )
        return requirement

    def validate_requirement_stock_line(
        self, requirement: ProductionMaterialRequirementModel, quantity: Decimal
    ) -> None:
        if requirement.source_type == ProductionMaterialSourceType.MANUAL.value:
            raise ValidationError("Manual production requirements cannot create stock movements.")
        if requirement.inventory_item_id is None:
            raise ValidationError("Requirement is not linked to inventory item.")
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.", {"field": "quantity"})

    async def ensure_output_serials(
        self, order: ProductionOrderModel, serial_numbers: list[str], quantity: Decimal
    ) -> list[InventorySerialModel]:
        product = await self.session.get(ItemModel, order.product_item_id)
        if product is None:
            raise EntityNotFoundError("Production output item not found.")
        if not product.track_serial_numbers:
            return []
        if quantity % 1 != 0:
            raise ValidationError("Serial-tracked output quantity must be whole units.")
        if len(serial_numbers) != int(quantity):
            raise ValidationError("Serial numbers count must match completed quantity.")
        if len(set(serial_numbers)) != len(serial_numbers):
            raise ConflictError("Duplicate serial number in request.")
        serials: list[InventorySerialModel] = []
        for serial_number in serial_numbers:
            serial = await self.session.scalar(
                select(InventorySerialModel).where(
                    InventorySerialModel.organization_id == order.organization_id,
                    InventorySerialModel.serial_number == serial_number,
                )
            )
            if serial is None:
                serial = InventorySerialModel(
                    organization_id=order.organization_id,
                    item_id=order.product_item_id,
                    serial_number=serial_number,
                    status=SerialStatus.AVAILABLE.value,
                    current_warehouse_id=order.finished_goods_warehouse_id,
                )
                self.session.add(serial)
                await self.session.flush()
            if serial.item_id != order.product_item_id:
                raise ValidationError("Serial number belongs to another item.")
            serials.append(serial)
        return serials

    async def audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor_id: UUID | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await SQLAlchemyAuditLogRepository(self.session).create(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                before_data=before,
                after_data=after,
                correlation_id=None,
            )
        )

    async def outbox(
        self, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict[str, Any]
    ) -> None:
        await SQLAlchemyOutboxRepository(self.session).create(
            OutboxEvent(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                occurred_at=datetime.now(UTC),
            )
        )

    async def commit_refresh(self, entity: object) -> None:
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(entity)


def decimal(value: Any) -> Decimal:
    return Decimal(str(value))
