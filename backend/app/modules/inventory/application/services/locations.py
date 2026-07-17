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
from .warehouses import WarehouseService


class LocationService(InventoryService):
    async def create(
        self, data: dict[str, Any], *, actor_id: UUID | None = None
    ) -> StorageLocationModel:
        warehouse = await WarehouseService(self.unit_of_work).get(data["warehouse_id"])
        if warehouse.organization_id != data["organization_id"]:
            raise ValidationError("Location warehouse must belong to the same organization.")
        await self._validate_parent(data["warehouse_id"], None, data.get("parent_id"))
        repository = StorageLocationRepository(self.session)
        if await repository.exists_by_code(data["warehouse_id"], data["code"]):
            raise ConflictError("Location code must be unique within warehouse.", {"field": "code"})
        location = await repository.create(StorageLocationModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_location",
            entity_id=location.id,
            actor_id=actor_id,
            after={"code": location.code, "name": location.name},
        )
        await self._commit()
        return location

    async def get(self, location_id: UUID) -> StorageLocationModel:
        location = await StorageLocationRepository(self.session).get(location_id)
        if location is None:
            raise EntityNotFoundError("Storage location not found.", {"id": str(location_id)})
        return location

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[StorageLocationModel], int]:
        return await StorageLocationRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        location_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> StorageLocationModel:
        repository = StorageLocationRepository(self.session)
        location = await self.get(location_id)
        self._ensure_version(location, expected_version)
        warehouse_id = data.get("warehouse_id", location.warehouse_id)
        await self._validate_parent(
            warehouse_id, location_id, data.get("parent_id", location.parent_id)
        )
        if await repository.exists_by_code(
            warehouse_id, data.get("code", location.code), exclude_id=location_id
        ):
            raise ConflictError("Location code must be unique within warehouse.", {"field": "code"})
        _apply_updates(location, data)
        await repository.update(location)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_location",
            entity_id=location.id,
            actor_id=actor_id,
        )
        await self._commit()
        return location

    async def deactivate(
        self, location_id: UUID, *, actor_id: UUID | None = None
    ) -> StorageLocationModel:
        location = await self.get(location_id)
        location.is_active = False
        await StorageLocationRepository(self.session).update(location)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_location",
            entity_id=location.id,
            actor_id=actor_id,
            after={"is_active": False},
        )
        await self._commit()
        return location

    async def _validate_parent(
        self, warehouse_id: UUID, location_id: UUID | None, parent_id: UUID | None
    ) -> None:
        if parent_id is None:
            return
        if parent_id == location_id:
            raise ValidationError("Location hierarchy cannot contain cycles.")
        parent = await self.get(parent_id)
        if parent.warehouse_id != warehouse_id:
            raise ValidationError("Parent location must belong to the same warehouse.")
        while parent.parent_id is not None:
            if parent.parent_id == location_id:
                raise ValidationError("Location hierarchy cannot contain cycles.")
            parent = await self.get(parent.parent_id)
            if parent.warehouse_id != warehouse_id:
                raise ValidationError("Parent location must belong to the same warehouse.")
