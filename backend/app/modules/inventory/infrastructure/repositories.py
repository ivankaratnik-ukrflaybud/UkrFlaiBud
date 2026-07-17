from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.inventory.infrastructure.models import (
    InventoryDocumentLineModel,
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
    UserSiteAccessModel,
    UserWarehouseAccessModel,
    WarehouseModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection

InventoryModel = (
    SiteModel
    | WarehouseModel
    | StorageLocationModel
    | UnitOfMeasureModel
    | ItemCategoryModel
    | ItemModel
    | InventoryLotModel
    | InventorySerialModel
    | InventoryDocumentModel
    | InventoryDocumentLineModel
    | InventoryMovementModel
    | StockBalanceModel
)


class InventoryQueryRepository[ModelT: InventoryModel]:
    sortable_fields: dict[str, Any] = {}

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model
        self.base_repository = SQLAlchemyRepository(session, model)

    async def create(self, entity: ModelT) -> ModelT:
        return await self.base_repository.create(entity)

    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> ModelT | None:
        return await self.base_repository.get(entity_id, include_deleted=include_deleted)

    async def update(self, entity: ModelT) -> ModelT:
        return await self.base_repository.update(entity)

    async def soft_delete(self, entity_id: UUID) -> None:
        await self.base_repository.soft_delete(entity_id)

    async def list(
        self,
        *,
        filters: dict[str, object],
        sort_by: str,
        sort_direction: SortDirection,
        limit: int,
        offset: int,
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        statement = self._apply_filters(
            self.base_repository._exclude_deleted(select(self.model), include_deleted),
            filters,
        )
        total = await self.session.scalar(statement.with_only_columns(func.count()).order_by(None))
        sort_column = self.sortable_fields.get(sort_by, self.sortable_fields["created_at"])
        ordered = statement.order_by(
            sort_column.desc() if sort_direction == SortDirection.DESC else sort_column.asc()
        )
        result = await self.session.scalars(ordered.limit(limit).offset(offset))
        return list(result.all()), total or 0

    async def exists(self, *conditions: Any) -> bool:
        statement = select(func.count()).select_from(self.model).where(and_(*conditions))
        return bool(await self.session.scalar(statement))

    def _apply_filters(
        self, statement: Select[tuple[ModelT]], filters: dict[str, object]
    ) -> Select[tuple[ModelT]]:
        return statement


class SiteRepository(InventoryQueryRepository[SiteModel]):
    sortable_fields = {
        "created_at": SiteModel.created_at,
        "code": SiteModel.code,
        "name": SiteModel.name,
        "is_active": SiteModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SiteModel)

    def _apply_filters(
        self, statement: Select[tuple[SiteModel]], filters: dict[str, object]
    ) -> Select[tuple[SiteModel]]:
        return _apply_code_name_active_filters(statement, SiteModel, filters)

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            SiteModel.organization_id == organization_id,
            SiteModel.code == code,
        ]
        if exclude_id:
            conditions.append(SiteModel.id != exclude_id)
        return await self.exists(*conditions)


class WarehouseRepository(InventoryQueryRepository[WarehouseModel]):
    sortable_fields = {
        "created_at": WarehouseModel.created_at,
        "code": WarehouseModel.code,
        "name": WarehouseModel.name,
        "is_active": WarehouseModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WarehouseModel)

    def _apply_filters(
        self, statement: Select[tuple[WarehouseModel]], filters: dict[str, object]
    ) -> Select[tuple[WarehouseModel]]:
        statement = _apply_code_name_active_filters(statement, WarehouseModel, filters)
        if site_id := filters.get("site_id"):
            statement = statement.where(WarehouseModel.site_id == site_id)
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(WarehouseModel.id.in_(warehouse_ids))
        site_ids = _sequence_filter(filters.get("site_ids"))
        if site_ids:
            statement = statement.where(WarehouseModel.site_id.in_(site_ids))
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            WarehouseModel.organization_id == organization_id,
            WarehouseModel.code == code,
        ]
        if exclude_id:
            conditions.append(WarehouseModel.id != exclude_id)
        return await self.exists(*conditions)


class StorageLocationRepository(InventoryQueryRepository[StorageLocationModel]):
    sortable_fields = {
        "created_at": StorageLocationModel.created_at,
        "code": StorageLocationModel.code,
        "name": StorageLocationModel.name,
        "is_active": StorageLocationModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StorageLocationModel)

    def _apply_filters(
        self, statement: Select[tuple[StorageLocationModel]], filters: dict[str, object]
    ) -> Select[tuple[StorageLocationModel]]:
        statement = _apply_code_name_active_filters(statement, StorageLocationModel, filters)
        if warehouse_id := filters.get("warehouse_id"):
            statement = statement.where(StorageLocationModel.warehouse_id == warehouse_id)
        if parent_id := filters.get("parent_id"):
            statement = statement.where(StorageLocationModel.parent_id == parent_id)
        return statement

    async def exists_by_code(
        self, warehouse_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            StorageLocationModel.warehouse_id == warehouse_id,
            StorageLocationModel.code == code,
        ]
        if exclude_id:
            conditions.append(StorageLocationModel.id != exclude_id)
        return await self.exists(*conditions)


class UnitRepository(InventoryQueryRepository[UnitOfMeasureModel]):
    sortable_fields = {
        "created_at": UnitOfMeasureModel.created_at,
        "code": UnitOfMeasureModel.code,
        "name": UnitOfMeasureModel.name,
        "is_active": UnitOfMeasureModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UnitOfMeasureModel)

    def _apply_filters(
        self, statement: Select[tuple[UnitOfMeasureModel]], filters: dict[str, object]
    ) -> Select[tuple[UnitOfMeasureModel]]:
        return _apply_code_name_active_filters(statement, UnitOfMeasureModel, filters)

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            UnitOfMeasureModel.organization_id == organization_id,
            UnitOfMeasureModel.code == code,
        ]
        if exclude_id:
            conditions.append(UnitOfMeasureModel.id != exclude_id)
        return await self.exists(*conditions)


class CategoryRepository(InventoryQueryRepository[ItemCategoryModel]):
    sortable_fields = {
        "created_at": ItemCategoryModel.created_at,
        "code": ItemCategoryModel.code,
        "name": ItemCategoryModel.name,
        "is_active": ItemCategoryModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemCategoryModel)

    def _apply_filters(
        self, statement: Select[tuple[ItemCategoryModel]], filters: dict[str, object]
    ) -> Select[tuple[ItemCategoryModel]]:
        statement = _apply_code_name_active_filters(statement, ItemCategoryModel, filters)
        if parent_id := filters.get("parent_id"):
            statement = statement.where(ItemCategoryModel.parent_id == parent_id)
        return statement

    async def exists_by_code(
        self, organization_id: UUID, code: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            ItemCategoryModel.organization_id == organization_id,
            ItemCategoryModel.code == code,
        ]
        if exclude_id:
            conditions.append(ItemCategoryModel.id != exclude_id)
        return await self.exists(*conditions)


class ItemRepository(InventoryQueryRepository[ItemModel]):
    sortable_fields = {
        "created_at": ItemModel.created_at,
        "sku": ItemModel.sku,
        "name": ItemModel.name,
        "is_active": ItemModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ItemModel)

    def _apply_filters(
        self, statement: Select[tuple[ItemModel]], filters: dict[str, object]
    ) -> Select[tuple[ItemModel]]:
        statement = _apply_code_name_active_filters(statement, ItemModel, filters, code_field="sku")
        if category_id := filters.get("category_id"):
            statement = statement.where(ItemModel.category_id == category_id)
        if item_type := filters.get("item_type"):
            statement = statement.where(ItemModel.item_type == item_type)
        if barcode := filters.get("barcode"):
            statement = statement.where(ItemModel.barcode == barcode)
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                or_(
                    ItemModel.sku.ilike(like),
                    ItemModel.name.ilike(like),
                    ItemModel.barcode == search,
                )
            )
        return statement

    async def exists_by_sku(
        self, organization_id: UUID, sku: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [ItemModel.organization_id == organization_id, ItemModel.sku == sku]
        if exclude_id:
            conditions.append(ItemModel.id != exclude_id)
        return await self.exists(*conditions)

    async def exists_by_barcode(
        self, organization_id: UUID, barcode: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            ItemModel.organization_id == organization_id,
            ItemModel.barcode == barcode,
        ]
        if exclude_id:
            conditions.append(ItemModel.id != exclude_id)
        return await self.exists(*conditions)


class LotRepository(InventoryQueryRepository[InventoryLotModel]):
    sortable_fields = {
        "created_at": InventoryLotModel.created_at,
        "lot_number": InventoryLotModel.lot_number,
        "expires_at": InventoryLotModel.expires_at,
        "is_active": InventoryLotModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryLotModel)

    def _apply_filters(
        self, statement: Select[tuple[InventoryLotModel]], filters: dict[str, object]
    ) -> Select[tuple[InventoryLotModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(InventoryLotModel.organization_id == organization_id)
        if item_id := filters.get("item_id"):
            statement = statement.where(InventoryLotModel.item_id == item_id)
        if lot_number := filters.get("lot_number"):
            statement = statement.where(InventoryLotModel.lot_number.ilike(f"%{lot_number}%"))
        if filters.get("is_active") is not None:
            statement = statement.where(InventoryLotModel.is_active == filters["is_active"])
        return statement

    async def exists_by_number(self, item_id: UUID, lot_number: str) -> bool:
        return await self.exists(
            InventoryLotModel.item_id == item_id,
            InventoryLotModel.lot_number == lot_number,
        )


class SerialRepository(InventoryQueryRepository[InventorySerialModel]):
    sortable_fields = {
        "created_at": InventorySerialModel.created_at,
        "serial_number": InventorySerialModel.serial_number,
        "status": InventorySerialModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventorySerialModel)

    def _apply_filters(
        self, statement: Select[tuple[InventorySerialModel]], filters: dict[str, object]
    ) -> Select[tuple[InventorySerialModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(InventorySerialModel.organization_id == organization_id)
        if item_id := filters.get("item_id"):
            statement = statement.where(InventorySerialModel.item_id == item_id)
        if warehouse_id := filters.get("warehouse_id"):
            statement = statement.where(InventorySerialModel.current_warehouse_id == warehouse_id)
        if serial_number := filters.get("serial_number"):
            statement = statement.where(
                InventorySerialModel.serial_number.ilike(f"%{serial_number}%")
            )
        if status := filters.get("status"):
            statement = statement.where(InventorySerialModel.status == status)
        return statement

    async def exists_by_number(
        self, organization_id: UUID, serial_number: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            InventorySerialModel.organization_id == organization_id,
            InventorySerialModel.serial_number == serial_number,
        ]
        if exclude_id:
            conditions.append(InventorySerialModel.id != exclude_id)
        return await self.exists(*conditions)


class DocumentRepository(InventoryQueryRepository[InventoryDocumentModel]):
    sortable_fields = {
        "created_at": InventoryDocumentModel.created_at,
        "document_date": InventoryDocumentModel.document_date,
        "document_number": InventoryDocumentModel.document_number,
        "status": InventoryDocumentModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryDocumentModel)

    def _apply_filters(
        self, statement: Select[tuple[InventoryDocumentModel]], filters: dict[str, object]
    ) -> Select[tuple[InventoryDocumentModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(InventoryDocumentModel.organization_id == organization_id)
        if document_type := filters.get("document_type"):
            statement = statement.where(InventoryDocumentModel.document_type == document_type)
        if status := filters.get("status"):
            statement = statement.where(InventoryDocumentModel.status == status)
        if source_warehouse_id := filters.get("source_warehouse_id"):
            statement = statement.where(
                InventoryDocumentModel.source_warehouse_id == source_warehouse_id
            )
        if destination_warehouse_id := filters.get("destination_warehouse_id"):
            statement = statement.where(
                InventoryDocumentModel.destination_warehouse_id == destination_warehouse_id
            )
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(
                or_(
                    InventoryDocumentModel.source_warehouse_id.in_(warehouse_ids),
                    InventoryDocumentModel.destination_warehouse_id.in_(warehouse_ids),
                )
            )
        return statement

    async def exists_by_number(
        self, organization_id: UUID, document_number: str, *, exclude_id: UUID | None = None
    ) -> bool:
        conditions: list[Any] = [
            InventoryDocumentModel.organization_id == organization_id,
            InventoryDocumentModel.document_number == document_number,
        ]
        if exclude_id:
            conditions.append(InventoryDocumentModel.id != exclude_id)
        return await self.exists(*conditions)


class DocumentLineRepository(InventoryQueryRepository[InventoryDocumentLineModel]):
    sortable_fields = {"created_at": InventoryDocumentLineModel.created_at}

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryDocumentLineModel)

    async def list_for_document(self, document_id: UUID) -> list[InventoryDocumentLineModel]:
        result = await self.session.scalars(
            select(InventoryDocumentLineModel)
            .where(InventoryDocumentLineModel.document_id == document_id)
            .order_by(InventoryDocumentLineModel.line_number.asc())
        )
        return list(result.all())

    async def next_line_number(self, document_id: UUID) -> int:
        number = await self.session.scalar(
            select(func.max(InventoryDocumentLineModel.line_number)).where(
                InventoryDocumentLineModel.document_id == document_id
            )
        )
        return (number or 0) + 1


class MovementRepository(InventoryQueryRepository[InventoryMovementModel]):
    sortable_fields = {
        "created_at": InventoryMovementModel.created_at,
        "occurred_at": InventoryMovementModel.occurred_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, InventoryMovementModel)

    def _apply_filters(
        self, statement: Select[tuple[InventoryMovementModel]], filters: dict[str, object]
    ) -> Select[tuple[InventoryMovementModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(InventoryMovementModel.organization_id == organization_id)
        if item_id := filters.get("item_id"):
            statement = statement.where(InventoryMovementModel.item_id == item_id)
        if warehouse_id := filters.get("warehouse_id"):
            statement = statement.where(InventoryMovementModel.warehouse_id == warehouse_id)
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(InventoryMovementModel.warehouse_id.in_(warehouse_ids))
        if document_id := filters.get("document_id"):
            statement = statement.where(InventoryMovementModel.document_id == document_id)
        return statement


class StockBalanceRepository(InventoryQueryRepository[StockBalanceModel]):
    sortable_fields = {
        "created_at": StockBalanceModel.updated_at,
        "updated_at": StockBalanceModel.updated_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, StockBalanceModel)

    def _apply_filters(
        self, statement: Select[tuple[StockBalanceModel]], filters: dict[str, object]
    ) -> Select[tuple[StockBalanceModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(StockBalanceModel.organization_id == organization_id)
        if item_id := filters.get("item_id"):
            statement = statement.where(StockBalanceModel.item_id == item_id)
        if warehouse_id := filters.get("warehouse_id"):
            statement = statement.where(StockBalanceModel.warehouse_id == warehouse_id)
        warehouse_ids = _sequence_filter(filters.get("warehouse_ids"))
        if warehouse_ids:
            statement = statement.where(StockBalanceModel.warehouse_id.in_(warehouse_ids))
        if location_id := filters.get("location_id"):
            statement = statement.where(StockBalanceModel.location_id == location_id)
        if lot_id := filters.get("lot_id"):
            statement = statement.where(StockBalanceModel.lot_id == lot_id)
        return statement

    async def get_dimension(
        self,
        *,
        organization_id: UUID,
        item_id: UUID,
        warehouse_id: UUID,
        location_id: UUID | None,
        lot_id: UUID | None,
        serial_id: UUID | None,
        for_update: bool = False,
    ) -> StockBalanceModel | None:
        statement = select(StockBalanceModel).where(
            StockBalanceModel.organization_id == organization_id,
            StockBalanceModel.item_id == item_id,
            StockBalanceModel.warehouse_id == warehouse_id,
            (
                StockBalanceModel.location_id.is_(None)
                if location_id is None
                else StockBalanceModel.location_id == location_id
            ),
            (
                StockBalanceModel.lot_id.is_(None)
                if lot_id is None
                else StockBalanceModel.lot_id == lot_id
            ),
            (
                StockBalanceModel.serial_id.is_(None)
                if serial_id is None
                else StockBalanceModel.serial_id == serial_id
            ),
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(StockBalanceModel | None, await self.session.scalar(statement))

    async def item_total(
        self, organization_id: UUID, item_id: UUID, warehouse_id: UUID | None = None
    ) -> Decimal:
        statement = select(func.coalesce(func.sum(StockBalanceModel.quantity), 0)).where(
            StockBalanceModel.organization_id == organization_id,
            StockBalanceModel.item_id == item_id,
        )
        if warehouse_id:
            statement = statement.where(StockBalanceModel.warehouse_id == warehouse_id)
        return await self.session.scalar(statement) or Decimal("0")


class InventoryScopeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def site_ids_for_user(self, user_id: UUID) -> set[UUID]:
        result = await self.session.scalars(
            select(UserSiteAccessModel.site_id).where(UserSiteAccessModel.user_id == user_id)
        )
        return set(result.all())

    async def warehouse_ids_for_user(self, user_id: UUID) -> set[UUID]:
        result = await self.session.scalars(
            select(UserWarehouseAccessModel.warehouse_id).where(
                UserWarehouseAccessModel.user_id == user_id
            )
        )
        return set(result.all())

    async def set_scope(
        self, user_id: UUID, site_ids: list[UUID], warehouse_ids: list[UUID]
    ) -> None:
        await self.session.execute(
            delete(UserSiteAccessModel).where(UserSiteAccessModel.user_id == user_id)
        )
        await self.session.execute(
            delete(UserWarehouseAccessModel).where(UserWarehouseAccessModel.user_id == user_id)
        )
        for site_id in site_ids:
            self.session.add(UserSiteAccessModel(user_id=user_id, site_id=site_id))
        for warehouse_id in warehouse_ids:
            self.session.add(UserWarehouseAccessModel(user_id=user_id, warehouse_id=warehouse_id))
        await self.session.flush()


def _apply_code_name_active_filters(
    statement: Select[tuple[Any]],
    model: Any,
    filters: dict[str, object],
    *,
    code_field: str = "code",
) -> Select[tuple[Any]]:
    if organization_id := filters.get("organization_id"):
        statement = statement.where(model.organization_id == organization_id)
    if code := filters.get("code"):
        statement = statement.where(getattr(model, code_field) == code)
    if name := filters.get("name"):
        statement = statement.where(model.name.ilike(f"%{name}%"))
    if filters.get("is_active") is not None:
        statement = statement.where(model.is_active == filters["is_active"])
    site_ids = _sequence_filter(filters.get("site_ids"))
    if site_ids:
        statement = statement.where(model.id.in_(site_ids))
    return statement


def _sequence_filter(value: object) -> Sequence[Any] | None:
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return None
