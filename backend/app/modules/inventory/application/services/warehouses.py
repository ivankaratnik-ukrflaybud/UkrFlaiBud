# ruff: noqa: F401,I001
from .common import (
    Any,
    UTC,
    datetime,
    Decimal,
    UUID,
    delete,
    func,
    or_,
    select,
    AsyncSession,
    AuditAction,
    AuditLog,
    OutboxEvent,
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
    UserService,
    UserModel,
    InventoryDocumentStatus,
    InventoryDocumentType,
    InventoryMovementKind,
    ItemType,
    SerialStatus,
    InventoryDocumentLineModel,
    InventoryDocumentLineSerialModel,
    InventoryDocumentModel,
    InventoryLotModel,
    InventoryMovementModel,
    InventorySerialModel,
    ItemCategoryModel,
    ItemModel,
    SiteModel,
    StockBalanceModel,
    StorageLocationModel,
    UnitOfMeasureModel,
    WarehouseModel,
    CategoryRepository,
    DocumentLineRepository,
    DocumentRepository,
    InventoryScopeRepository,
    ItemRepository,
    LotRepository,
    MovementRepository,
    SerialRepository,
    SiteRepository,
    StockBalanceRepository,
    StorageLocationRepository,
    UnitRepository,
    WarehouseRepository,
    EmployeeModel,
    OrganizationModel,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyOutboxRepository,
    SQLAlchemyUnitOfWork,
    PageRequest,
    SortDirection,
    STOCK_IN_TYPES,
    STOCK_OUT_TYPES,
    InventoryService,
    _apply_updates,
)
from .scope import InventoryScopeService
from .sites import SiteService


class WarehouseService(InventoryService):
    async def create(self, data: dict[str, Any], *, actor_id: UUID | None = None) -> WarehouseModel:
        site = await SiteService(self.unit_of_work).get(data["site_id"])
        if not site.is_active:
            raise ValidationError("Inactive site cannot receive new warehouses.")
        if site.organization_id != data["organization_id"]:
            raise ValidationError("Warehouse site must belong to the same organization.")
        await self._ensure_employee(data["organization_id"], data.get("responsible_employee_id"))
        repository = WarehouseRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError(
                "Warehouse code must be unique within organization.", {"field": "code"}
            )
        warehouse = await repository.create(WarehouseModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_warehouse",
            entity_id=warehouse.id,
            actor_id=actor_id,
            after={"code": warehouse.code, "name": warehouse.name},
        )
        await self._commit()
        return warehouse

    async def get(self, warehouse_id: UUID, *, include_deleted: bool = False) -> WarehouseModel:
        warehouse = await WarehouseRepository(self.session).get(
            warehouse_id, include_deleted=include_deleted
        )
        if warehouse is None:
            raise EntityNotFoundError("Warehouse not found.", {"id": str(warehouse_id)})
        return warehouse

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: UserModel | None = None,
    ) -> tuple[list[WarehouseModel], int]:
        if user and not user.is_superuser:
            allowed = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(user)
            if not allowed:
                return [], 0
            filters = {**filters, "warehouse_ids": allowed}
        return await WarehouseRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        warehouse_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> WarehouseModel:
        repository = WarehouseRepository(self.session)
        warehouse = await self.get(warehouse_id)
        self._ensure_version(warehouse, expected_version)
        organization_id = data.get("organization_id", warehouse.organization_id)
        site_id = data.get("site_id", warehouse.site_id)
        site = await SiteService(self.unit_of_work).get(site_id)
        if site.organization_id != organization_id:
            raise ValidationError("Warehouse site must belong to the same organization.")
        await self._ensure_employee(
            organization_id, data.get("responsible_employee_id", warehouse.responsible_employee_id)
        )
        code = data.get("code", warehouse.code)
        if await repository.exists_by_code(organization_id, code, exclude_id=warehouse_id):
            raise ConflictError(
                "Warehouse code must be unique within organization.", {"field": "code"}
            )
        before = {"code": warehouse.code, "name": warehouse.name, "is_active": warehouse.is_active}
        _apply_updates(warehouse, data)
        await repository.update(warehouse)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_warehouse",
            entity_id=warehouse.id,
            actor_id=actor_id,
            before=before,
            after={
                "code": warehouse.code,
                "name": warehouse.name,
                "is_active": warehouse.is_active,
            },
        )
        await self._commit()
        return warehouse

    async def deactivate(
        self, warehouse_id: UUID, *, actor_id: UUID | None = None
    ) -> WarehouseModel:
        warehouse = await self.get(warehouse_id)
        warehouse.is_active = False
        await WarehouseRepository(self.session).update(warehouse)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_warehouse",
            entity_id=warehouse.id,
            actor_id=actor_id,
            after={"is_active": False},
        )
        await self._commit()
        return warehouse
