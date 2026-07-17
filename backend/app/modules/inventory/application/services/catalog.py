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


class CatalogService(InventoryService):
    async def create_unit(
        self, data: dict[str, Any], *, actor_id: UUID | None = None
    ) -> UnitOfMeasureModel:
        await self._ensure_organization(data["organization_id"])
        repository = UnitRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError("Unit code must be unique within organization.", {"field": "code"})
        unit = await repository.create(UnitOfMeasureModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_unit",
            entity_id=unit.id,
            actor_id=actor_id,
            after={"code": unit.code, "name": unit.name},
        )
        await self._commit()
        return unit

    async def get_unit(self, unit_id: UUID) -> UnitOfMeasureModel:
        unit = await UnitRepository(self.session).get(unit_id)
        if unit is None:
            raise EntityNotFoundError("Unit not found.", {"id": str(unit_id)})
        return unit

    async def list_units(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[UnitOfMeasureModel], int]:
        return await UnitRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update_unit(
        self,
        unit_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> UnitOfMeasureModel:
        unit = await self.get_unit(unit_id)
        self._ensure_version(unit, expected_version)
        repository = UnitRepository(self.session)
        if await repository.exists_by_code(
            data.get("organization_id", unit.organization_id),
            data.get("code", unit.code),
            exclude_id=unit_id,
        ):
            raise ConflictError("Unit code must be unique within organization.", {"field": "code"})
        _apply_updates(unit, data)
        await repository.update(unit)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_unit",
            entity_id=unit.id,
            actor_id=actor_id,
        )
        await self._commit()
        return unit

    async def create_category(
        self, data: dict[str, Any], *, actor_id: UUID | None = None
    ) -> ItemCategoryModel:
        await self._ensure_organization(data["organization_id"])
        await self._validate_category_parent(data["organization_id"], None, data.get("parent_id"))
        repository = CategoryRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError(
                "Category code must be unique within organization.", {"field": "code"}
            )
        category = await repository.create(ItemCategoryModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_category",
            entity_id=category.id,
            actor_id=actor_id,
            after={"code": category.code, "name": category.name},
        )
        await self._commit()
        return category

    async def get_category(self, category_id: UUID) -> ItemCategoryModel:
        category = await CategoryRepository(self.session).get(category_id)
        if category is None:
            raise EntityNotFoundError("Category not found.", {"id": str(category_id)})
        return category

    async def list_categories(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[ItemCategoryModel], int]:
        return await CategoryRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update_category(
        self,
        category_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> ItemCategoryModel:
        category = await self.get_category(category_id)
        self._ensure_version(category, expected_version)
        organization_id = data.get("organization_id", category.organization_id)
        await self._validate_category_parent(
            organization_id, category_id, data.get("parent_id", category.parent_id)
        )
        repository = CategoryRepository(self.session)
        if await repository.exists_by_code(
            organization_id, data.get("code", category.code), exclude_id=category_id
        ):
            raise ConflictError(
                "Category code must be unique within organization.", {"field": "code"}
            )
        _apply_updates(category, data)
        await repository.update(category)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_category",
            entity_id=category.id,
            actor_id=actor_id,
        )
        await self._commit()
        return category

    async def create_item(self, data: dict[str, Any], *, actor_id: UUID | None = None) -> ItemModel:
        await self._validate_item_relations(data)
        repository = ItemRepository(self.session)
        if await repository.exists_by_sku(data["organization_id"], data["sku"]):
            raise ConflictError("Item SKU must be unique within organization.", {"field": "sku"})
        if data.get("barcode") and await repository.exists_by_barcode(
            data["organization_id"], data["barcode"]
        ):
            raise ConflictError(
                "Item barcode must be unique within organization.", {"field": "barcode"}
            )
        item = await repository.create(ItemModel(**data))
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_item",
            entity_id=item.id,
            actor_id=actor_id,
            after={"sku": item.sku, "name": item.name},
        )
        await self._outbox(
            "inventory.item.created",
            "inventory_item",
            item.id,
            {"sku": item.sku, "organization_id": str(item.organization_id)},
        )
        await self._commit()
        return item

    async def get_item(self, item_id: UUID) -> ItemModel:
        item = await ItemRepository(self.session).get(item_id)
        if item is None:
            raise EntityNotFoundError("Item not found.", {"id": str(item_id)})
        return item

    async def list_items(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[ItemModel], int]:
        return await ItemRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update_item(
        self,
        item_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID | None = None,
    ) -> ItemModel:
        item = await self.get_item(item_id)
        self._ensure_version(item, expected_version)
        merged = {**{column: getattr(item, column) for column in data}, **data}
        merged["organization_id"] = data.get("organization_id", item.organization_id)
        merged["category_id"] = data.get("category_id", item.category_id)
        merged["unit_of_measure_id"] = data.get("unit_of_measure_id", item.unit_of_measure_id)
        merged["default_warehouse_id"] = data.get("default_warehouse_id", item.default_warehouse_id)
        await self._validate_item_relations(merged)
        repository = ItemRepository(self.session)
        if await repository.exists_by_sku(
            merged["organization_id"], data.get("sku", item.sku), exclude_id=item_id
        ):
            raise ConflictError("Item SKU must be unique within organization.", {"field": "sku"})
        barcode = data.get("barcode", item.barcode)
        if barcode and await repository.exists_by_barcode(
            merged["organization_id"], barcode, exclude_id=item_id
        ):
            raise ConflictError(
                "Item barcode must be unique within organization.", {"field": "barcode"}
            )
        before = {"sku": item.sku, "name": item.name, "is_active": item.is_active}
        _apply_updates(item, data)
        await repository.update(item)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_item",
            entity_id=item.id,
            actor_id=actor_id,
            before=before,
            after={"sku": item.sku, "name": item.name, "is_active": item.is_active},
        )
        await self._commit()
        return item

    async def deactivate_item(self, item_id: UUID, *, actor_id: UUID | None = None) -> ItemModel:
        item = await self.get_item(item_id)
        item.is_active = False
        await ItemRepository(self.session).update(item)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_item",
            entity_id=item.id,
            actor_id=actor_id,
            after={"is_active": False},
        )
        await self._commit()
        return item

    async def _validate_category_parent(
        self, organization_id: UUID, category_id: UUID | None, parent_id: UUID | None
    ) -> None:
        if parent_id is None:
            return
        if parent_id == category_id:
            raise ValidationError("Category hierarchy cannot contain cycles.")
        parent = await self.get_category(parent_id)
        if parent.organization_id != organization_id:
            raise ValidationError("Parent category must belong to the same organization.")
        while parent.parent_id is not None:
            if parent.parent_id == category_id:
                raise ValidationError("Category hierarchy cannot contain cycles.")
            parent = await self.get_category(parent.parent_id)
            if parent.organization_id != organization_id:
                raise ValidationError("Parent category must belong to the same organization.")

    async def _validate_item_relations(self, data: dict[str, Any]) -> None:
        category = await self.get_category(data["category_id"])
        unit = await self.get_unit(data["unit_of_measure_id"])
        if (
            category.organization_id != data["organization_id"]
            or unit.organization_id != data["organization_id"]
        ):
            raise ValidationError("Item category and unit must belong to the same organization.")
        if data.get("default_warehouse_id"):
            warehouse = await WarehouseService(self.unit_of_work).get(data["default_warehouse_id"])
            if warehouse.organization_id != data["organization_id"]:
                raise ValidationError("Default warehouse must belong to the same organization.")
        minimum_stock = Decimal(str(data.get("minimum_stock", 0)))
        maximum_stock = data.get("maximum_stock")
        if minimum_stock < 0:
            raise ValidationError("Minimum stock cannot be negative.", {"field": "minimum_stock"})
        if maximum_stock is not None and Decimal(str(maximum_stock)) < minimum_stock:
            raise ValidationError(
                "Maximum stock cannot be below minimum stock.", {"field": "maximum_stock"}
            )
        if data.get("track_serial_numbers") and unit.precision != 0:
            raise ValidationError("Serial-tracked items must use whole units.")
