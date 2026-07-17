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


class InventoryScopeService(InventoryService):
    async def accessible_site_ids(self, user: UserModel) -> set[UUID] | None:
        if user.is_superuser:
            return None
        scope_repository = InventoryScopeRepository(self.session)
        return await scope_repository.site_ids_for_user(user.id)

    async def accessible_warehouse_ids(self, user: UserModel) -> set[UUID] | None:
        if user.is_superuser:
            return None
        scope_repository = InventoryScopeRepository(self.session)
        explicit_warehouses = await scope_repository.warehouse_ids_for_user(user.id)
        site_ids = await scope_repository.site_ids_for_user(user.id)
        if site_ids:
            result = await self.session.scalars(
                select(WarehouseModel.id).where(
                    WarehouseModel.site_id.in_(site_ids), WarehouseModel.deleted_at.is_(None)
                )
            )
            explicit_warehouses.update(result.all())
        return explicit_warehouses

    async def ensure_warehouse_access(self, user: UserModel, warehouse_id: UUID | None) -> None:
        if warehouse_id is None or user.is_superuser:
            return
        allowed = await self.accessible_warehouse_ids(user)
        if warehouse_id not in (allowed or set()):
            raise PermissionDeniedError("You do not have access to this warehouse.")

    async def get_user_scope(self, user_id: UUID) -> dict[str, list[UUID]]:
        await UserService(self.unit_of_work).get(user_id)
        repository = InventoryScopeRepository(self.session)
        return {
            "site_ids": sorted(await repository.site_ids_for_user(user_id), key=str),
            "warehouse_ids": sorted(await repository.warehouse_ids_for_user(user_id), key=str),
        }

    async def set_user_scope(
        self, user_id: UUID, site_ids: list[UUID], warehouse_ids: list[UUID], *, actor_id: UUID
    ) -> dict[str, list[UUID]]:
        await UserService(self.unit_of_work).get(user_id)
        from .sites import SiteService
        from .warehouses import WarehouseService

        for site_id in site_ids:
            await SiteService(self.unit_of_work).get(site_id)
        for warehouse_id in warehouse_ids:
            await WarehouseService(self.unit_of_work).get(warehouse_id)
        before = await self.get_user_scope(user_id)
        await InventoryScopeRepository(self.session).set_scope(user_id, site_ids, warehouse_ids)
        after = {"site_ids": site_ids, "warehouse_ids": warehouse_ids}
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="user_inventory_scope",
            entity_id=user_id,
            actor_id=actor_id,
            before={key: [str(value) for value in values] for key, values in before.items()},
            after={key: [str(value) for value in values] for key, values in after.items()},
        )
        await self._commit()
        return after
