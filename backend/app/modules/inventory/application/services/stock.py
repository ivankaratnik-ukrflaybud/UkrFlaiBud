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


class StockService(InventoryService):
    async def list_balances(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: UserModel | None = None,
    ) -> tuple[list[StockBalanceModel], int]:
        if user and not user.is_superuser:
            allowed = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(user)
            if not allowed:
                return [], 0
            filters = {**filters, "warehouse_ids": allowed}
        return await StockBalanceRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def list_movements(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: UserModel | None = None,
    ) -> tuple[list[InventoryMovementModel], int]:
        if user and not user.is_superuser:
            allowed = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(user)
            if not allowed:
                return [], 0
            filters = {**filters, "warehouse_ids": allowed}
        return await MovementRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def low_stock(
        self, organization_id: UUID, *, user: UserModel | None = None
    ) -> list[dict[str, Any]]:
        allowed = None
        if user and not user.is_superuser:
            allowed = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(user)
            if not allowed:
                return []
        statement = (
            select(
                ItemModel.id,
                ItemModel.sku,
                ItemModel.name,
                ItemModel.minimum_stock,
                func.coalesce(func.sum(StockBalanceModel.quantity), 0).label("quantity"),
            )
            .outerjoin(StockBalanceModel, StockBalanceModel.item_id == ItemModel.id)
            .where(
                ItemModel.organization_id == organization_id,
                ItemModel.deleted_at.is_(None),
                ItemModel.minimum_stock > 0,
            )
            .group_by(ItemModel.id)
        )
        if allowed is not None:
            statement = statement.where(
                or_(
                    StockBalanceModel.warehouse_id.in_(allowed),
                    StockBalanceModel.warehouse_id.is_(None),
                )
            )
        rows = (await self.session.execute(statement)).all()
        return [
            {
                "item_id": row.id,
                "sku": row.sku,
                "name": row.name,
                "minimum_stock": row.minimum_stock,
                "quantity": row.quantity,
            }
            for row in rows
            if Decimal(row.quantity) < Decimal(row.minimum_stock)
        ]
