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
from .catalog import CatalogService
from .warehouses import WarehouseService


class TrackingService(InventoryService):
    async def create_lot(
        self, data: dict[str, Any], *, actor_id: UUID | None = None
    ) -> InventoryLotModel:
        item = await CatalogService(self.unit_of_work).get_item(data["item_id"])
        if item.organization_id != data["organization_id"]:
            raise ValidationError("Lot item must belong to the same organization.")
        if not item.track_lots:
            raise ValidationError("Lots are only allowed for lot-tracked items.")
        repository = LotRepository(self.session)
        if await repository.exists_by_number(data["item_id"], data["lot_number"]):
            raise ConflictError("Lot number must be unique per item.", {"field": "lot_number"})
        lot = await repository.create(InventoryLotModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_lot",
            entity_id=lot.id,
            actor_id=actor_id,
        )
        await self._commit()
        return lot

    async def get_lot(self, lot_id: UUID) -> InventoryLotModel:
        lot = await LotRepository(self.session).get(lot_id)
        if lot is None:
            raise EntityNotFoundError("Lot not found.", {"id": str(lot_id)})
        return lot

    async def list_lots(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[InventoryLotModel], int]:
        return await LotRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def create_serial(
        self, data: dict[str, Any], *, actor_id: UUID | None = None
    ) -> InventorySerialModel:
        item = await CatalogService(self.unit_of_work).get_item(data["item_id"])
        if item.organization_id != data["organization_id"]:
            raise ValidationError("Serial item must belong to the same organization.")
        if not item.track_serial_numbers:
            raise ValidationError("Serials are only allowed for serial-tracked items.")
        if data.get("current_warehouse_id"):
            warehouse = await WarehouseService(self.unit_of_work).get(data["current_warehouse_id"])
            if warehouse.organization_id != data["organization_id"]:
                raise ValidationError("Serial warehouse must belong to the same organization.")
        repository = SerialRepository(self.session)
        if await repository.exists_by_number(data["organization_id"], data["serial_number"]):
            raise ConflictError("Serial number must be unique.", {"field": "serial_number"})
        serial = await repository.create(InventorySerialModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_serial",
            entity_id=serial.id,
            actor_id=actor_id,
        )
        await self._commit()
        return serial

    async def get_serial(self, serial_id: UUID) -> InventorySerialModel:
        serial = await SerialRepository(self.session).get(serial_id)
        if serial is None:
            raise EntityNotFoundError("Serial not found.", {"id": str(serial_id)})
        return serial

    async def list_serials(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[InventorySerialModel], int]:
        return await SerialRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update_serial_status(
        self, serial_id: UUID, status: SerialStatus, *, actor_id: UUID | None = None
    ) -> InventorySerialModel:
        serial = await self.get_serial(serial_id)
        before = {"status": serial.status}
        serial.status = status.value
        await SerialRepository(self.session).update(serial)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_serial",
            entity_id=serial.id,
            actor_id=actor_id,
            before=before,
            after={"status": serial.status},
        )
        await self._outbox(
            "inventory.serial.status_changed",
            "inventory_serial",
            serial.id,
            {"status": serial.status},
        )
        await self._commit()
        return serial
