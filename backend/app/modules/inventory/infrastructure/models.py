from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import EntityMixin, IdMixin, TimestampMixin, VersionMixin
from app.modules.inventory.domain.entities import (
    InventoryDocumentStatus,
    ItemType,
    SerialStatus,
    StorageLocationType,
    WarehouseType,
)


class SiteModel(EntityMixin, Base):
    __tablename__ = "inventory_sites"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_inventory_sites_organization_code"),
        Index("ix_inventory_sites_organization_id", "organization_id"),
        Index("ix_inventory_sites_is_active", "is_active"),
        Index("ix_inventory_sites_name", "name"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class WarehouseModel(EntityMixin, Base):
    __tablename__ = "inventory_warehouses"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_inventory_warehouses_organization_code"
        ),
        CheckConstraint(
            "warehouse_type IN ('main', 'production', 'raw_material', 'components', "
            "'finished_goods', 'quarantine', 'scrap', 'other')",
            name="ck_inventory_warehouses_type",
        ),
        Index("ix_inventory_warehouses_organization_id", "organization_id"),
        Index("ix_inventory_warehouses_site_id", "site_id"),
        Index("ix_inventory_warehouses_is_active", "is_active"),
        Index("ix_inventory_warehouses_name", "name"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_sites.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    warehouse_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=WarehouseType.MAIN.value,
        server_default=WarehouseType.MAIN.value,
    )
    responsible_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True
    )
    allow_negative_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class StorageLocationModel(EntityMixin, Base):
    __tablename__ = "inventory_storage_locations"
    __table_args__ = (
        UniqueConstraint("warehouse_id", "code", name="uq_inventory_locations_warehouse_code"),
        CheckConstraint("id <> parent_id", name="ck_inventory_locations_not_self_parent"),
        CheckConstraint(
            "location_type IN ('zone', 'rack', 'shelf', 'bin', 'floor', "
            "'quarantine', 'scrap', 'other')",
            name="ck_inventory_locations_type",
        ),
        Index("ix_inventory_locations_organization_id", "organization_id"),
        Index("ix_inventory_locations_warehouse_id", "warehouse_id"),
        Index("ix_inventory_locations_parent_id", "parent_id"),
        Index("ix_inventory_locations_barcode", "barcode"),
        Index("ix_inventory_locations_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=StorageLocationType.BIN.value,
        server_default=StorageLocationType.BIN.value,
    )
    barcode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class UnitOfMeasureModel(EntityMixin, Base):
    __tablename__ = "inventory_units"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_inventory_units_organization_code"),
        CheckConstraint("precision >= 0 AND precision <= 6", name="ck_inventory_units_precision"),
        Index("ix_inventory_units_organization_id", "organization_id"),
        Index("ix_inventory_units_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    precision: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ItemCategoryModel(EntityMixin, Base):
    __tablename__ = "inventory_item_categories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_inventory_categories_organization_code"
        ),
        CheckConstraint("id <> parent_id", name="ck_inventory_categories_not_self_parent"),
        Index("ix_inventory_categories_organization_id", "organization_id"),
        Index("ix_inventory_categories_parent_id", "parent_id"),
        Index("ix_inventory_categories_name", "name"),
        Index("ix_inventory_categories_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    parent_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_item_categories.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ItemModel(EntityMixin, Base):
    __tablename__ = "inventory_items"
    __table_args__ = (
        UniqueConstraint("organization_id", "sku", name="uq_inventory_items_organization_sku"),
        CheckConstraint(
            "item_type IN ('raw_material', 'component', 'semi_finished', 'finished_good', "
            "'consumable', 'tool', 'spare_part', 'packaging', 'service', 'other')",
            name="ck_inventory_items_type",
        ),
        CheckConstraint("minimum_stock >= 0", name="ck_inventory_items_minimum_stock"),
        CheckConstraint(
            "maximum_stock IS NULL OR maximum_stock >= minimum_stock",
            name="ck_inventory_items_maximum_stock",
        ),
        CheckConstraint(
            "NOT (track_serial_numbers = true AND track_lots = true)",
            name="ck_inventory_items_single_tracking_mode",
        ),
        Index("ix_inventory_items_organization_id", "organization_id"),
        Index("ix_inventory_items_category_id", "category_id"),
        Index("ix_inventory_items_unit_id", "unit_of_measure_id"),
        Index("ix_inventory_items_sku", "sku"),
        Index("ix_inventory_items_name", "name"),
        Index(
            "ix_inventory_items_barcode",
            "barcode",
            unique=True,
            postgresql_where=text("barcode IS NOT NULL"),
        ),
        Index("ix_inventory_items_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    sku: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_item_categories.id", ondelete="RESTRICT")
    )
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    item_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ItemType.COMPONENT.value,
        server_default=ItemType.COMPONENT.value,
    )
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(128), nullable=True)
    internal_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drawing_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    specifications: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    track_lots: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    track_serial_numbers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    minimum_stock: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    maximum_stock: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    default_warehouse_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="SET NULL")
    )
    image_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class InventoryLotModel(EntityMixin, Base):
    __tablename__ = "inventory_lots"
    __table_args__ = (
        UniqueConstraint("item_id", "lot_number", name="uq_inventory_lots_item_number"),
        Index("ix_inventory_lots_organization_id", "organization_id"),
        Index("ix_inventory_lots_item_id", "item_id"),
        Index("ix_inventory_lots_lot_number", "lot_number"),
        Index("ix_inventory_lots_expires_at", "expires_at"),
        Index("ix_inventory_lots_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    lot_number: Mapped[str] = mapped_column(String(128), nullable=False)
    manufactured_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class InventorySerialModel(EntityMixin, Base):
    __tablename__ = "inventory_serials"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "serial_number", name="uq_inventory_serials_organization_number"
        ),
        CheckConstraint(
            "status IN ('available', 'reserved', 'issued', 'in_production', "
            "'installed', 'quarantine', 'scrapped')",
            name="ck_inventory_serials_status",
        ),
        Index("ix_inventory_serials_organization_id", "organization_id"),
        Index("ix_inventory_serials_item_id", "item_id"),
        Index("ix_inventory_serials_number", "serial_number"),
        Index("ix_inventory_serials_status", "status"),
        Index("ix_inventory_serials_current_warehouse_id", "current_warehouse_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    serial_number: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SerialStatus.AVAILABLE.value,
        server_default=SerialStatus.AVAILABLE.value,
    )
    current_warehouse_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="SET NULL")
    )
    current_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="SET NULL")
    )
    lot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class InventoryDocumentModel(EntityMixin, Base):
    __tablename__ = "inventory_documents"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "document_number", name="uq_inventory_documents_organization_number"
        ),
        CheckConstraint(
            "document_type IN ('receipt', 'issue', 'transfer', 'adjustment_in', "
            "'adjustment_out', 'return_in', 'return_out')",
            name="ck_inventory_documents_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'cancelled')", name="ck_inventory_documents_status"
        ),
        Index("ix_inventory_documents_organization_id", "organization_id"),
        Index("ix_inventory_documents_number", "document_number"),
        Index("ix_inventory_documents_date", "document_date"),
        Index("ix_inventory_documents_status", "status"),
        Index("ix_inventory_documents_source_warehouse_id", "source_warehouse_id"),
        Index("ix_inventory_documents_destination_warehouse_id", "destination_warehouse_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    document_number: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=InventoryDocumentStatus.DRAFT.value,
        server_default=InventoryDocumentStatus.DRAFT.value,
    )
    document_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    source_warehouse_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    destination_warehouse_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    responsible_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class InventoryDocumentLineModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "inventory_document_lines"
    __table_args__ = (
        UniqueConstraint("document_id", "line_number", name="uq_inventory_document_lines_number"),
        CheckConstraint("quantity > 0", name="ck_inventory_document_lines_quantity_positive"),
        Index("ix_inventory_document_lines_document_id", "document_id"),
        Index("ix_inventory_document_lines_item_id", "item_id"),
        Index("ix_inventory_document_lines_lot_id", "lot_id"),
    )

    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="CASCADE")
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    source_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    destination_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class InventoryDocumentLineSerialModel(Base):
    __tablename__ = "inventory_document_line_serials"
    __table_args__ = (
        UniqueConstraint("line_id", "serial_id", name="uq_inventory_line_serials_pair"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    line_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_document_lines.id", ondelete="CASCADE")
    )
    serial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_serials.id", ondelete="RESTRICT")
    )


class InventoryMovementModel(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        CheckConstraint(
            "movement_kind IN ('receipt', 'issue', 'transfer_out', 'transfer_in', 'adjustment_in', "
            "'adjustment_out', 'return_in', 'return_out', 'reversal')",
            name="ck_inventory_movements_kind",
        ),
        CheckConstraint("quantity_delta <> 0", name="ck_inventory_movements_quantity_delta"),
        Index("ix_inventory_movements_organization_id", "organization_id"),
        Index("ix_inventory_movements_document_id", "document_id"),
        Index(
            "ix_inventory_movements_item_warehouse_date", "item_id", "warehouse_id", "occurred_at"
        ),
        Index("ix_inventory_movements_location_id", "location_id"),
        Index("ix_inventory_movements_lot_id", "lot_id"),
        Index("ix_inventory_movements_serial_id", "serial_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="RESTRICT")
    )
    document_line_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_document_lines.id", ondelete="RESTRICT")
    )
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="RESTRICT")
    )
    serial_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_serials.id", ondelete="RESTRICT")
    )
    quantity_delta: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    movement_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    reversal_of_movement_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_movements.id", ondelete="RESTRICT")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class StockBalanceModel(Base):
    __tablename__ = "inventory_stock_balances"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "item_id",
            "warehouse_id",
            "location_id",
            "lot_id",
            "serial_id",
            name="uq_inventory_stock_balance_dimensions",
        ),
        CheckConstraint("quantity >= 0", name="ck_inventory_stock_balances_nonnegative"),
        Index("ix_inventory_stock_balances_organization_id", "organization_id"),
        Index("ix_inventory_stock_balances_item_id", "item_id"),
        Index("ix_inventory_stock_balances_warehouse_id", "warehouse_id"),
        Index("ix_inventory_stock_balances_location_id", "location_id"),
        Index("ix_inventory_stock_balances_lot_id", "lot_id"),
        Index("ix_inventory_stock_balances_serial_id", "serial_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    lot_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_lots.id", ondelete="RESTRICT")
    )
    serial_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_serials.id", ondelete="RESTRICT")
    )
    quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class UserSiteAccessModel(Base):
    __tablename__ = "user_site_access"
    __table_args__ = (
        UniqueConstraint("user_id", "site_id", name="uq_user_site_access_pair"),
        Index("ix_user_site_access_user_id", "user_id"),
        Index("ix_user_site_access_site_id", "site_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_sites.id", ondelete="CASCADE")
    )


class UserWarehouseAccessModel(Base):
    __tablename__ = "user_warehouse_access"
    __table_args__ = (
        UniqueConstraint("user_id", "warehouse_id", name="uq_user_warehouse_access_pair"),
        Index("ix_user_warehouse_access_user_id", "user_id"),
        Index("ix_user_warehouse_access_warehouse_id", "warehouse_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="CASCADE")
    )
