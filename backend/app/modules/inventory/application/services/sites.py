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


class SiteService(InventoryService):
    async def create(self, data: dict[str, Any], *, actor_id: UUID | None = None) -> SiteModel:
        await self._ensure_organization(data["organization_id"])
        repository = SiteRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError("Site code must be unique within organization.", {"field": "code"})
        site = await repository.create(SiteModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_site",
            entity_id=site.id,
            actor_id=actor_id,
            after={"code": site.code, "name": site.name},
        )
        await self._commit()
        return site

    async def get(self, site_id: UUID, *, include_deleted: bool = False) -> SiteModel:
        site = await SiteRepository(self.session).get(site_id, include_deleted=include_deleted)
        if site is None:
            raise EntityNotFoundError("Site not found.", {"id": str(site_id)})
        return site

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: UserModel | None = None,
    ) -> tuple[list[SiteModel], int]:
        if user and not user.is_superuser:
            site_ids = await InventoryScopeService(self.unit_of_work).accessible_site_ids(user)
            warehouse_ids = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(
                user
            )
            if warehouse_ids:
                result = await self.session.scalars(
                    select(WarehouseModel.site_id).where(WarehouseModel.id.in_(warehouse_ids))
                )
                site_ids = (site_ids or set()) | set(result.all())
            if not site_ids:
                return [], 0
            filters = {**filters, "site_ids": site_ids}
        return await SiteRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        site_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> SiteModel:
        repository = SiteRepository(self.session)
        site = await self.get(site_id)
        self._ensure_version(site, expected_version)
        code = data.get("code", site.code)
        organization_id = data.get("organization_id", site.organization_id)
        await self._ensure_organization(organization_id)
        if await repository.exists_by_code(organization_id, code, exclude_id=site_id):
            raise ConflictError("Site code must be unique within organization.", {"field": "code"})
        before = {"code": site.code, "name": site.name, "is_active": site.is_active}
        _apply_updates(site, data)
        await repository.update(site)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_site",
            entity_id=site.id,
            actor_id=actor_id,
            before=before,
            after={"code": site.code, "name": site.name, "is_active": site.is_active},
        )
        await self._commit()
        return site

    async def deactivate(self, site_id: UUID, *, actor_id: UUID | None = None) -> SiteModel:
        site = await self.get(site_id)
        site.is_active = False
        await SiteRepository(self.session).update(site)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_site",
            entity_id=site.id,
            actor_id=actor_id,
            after={"is_active": False},
        )
        await self._commit()
        return site
