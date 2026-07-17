from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.inventory.domain.entities import (
    InventoryDocumentType,
    ItemType,
    SerialStatus,
    StorageLocationType,
    WarehouseType,
)


class MutableEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int


class SiteCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    is_active: bool = True


class SiteUpdate(BaseModel):
    version: int
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    address: str | None = None
    is_active: bool | None = None


class SiteResponse(MutableEntityResponse):
    organization_id: UUID
    code: str
    name: str
    description: str | None
    address: str | None
    is_active: bool


class WarehouseCreate(BaseModel):
    organization_id: UUID
    site_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    warehouse_type: WarehouseType = WarehouseType.MAIN
    responsible_employee_id: UUID | None = None
    allow_negative_stock: bool = False
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    version: int
    site_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    warehouse_type: WarehouseType | None = None
    responsible_employee_id: UUID | None = None
    allow_negative_stock: bool | None = None
    is_active: bool | None = None


class WarehouseResponse(MutableEntityResponse):
    organization_id: UUID
    site_id: UUID
    code: str
    name: str
    description: str | None
    warehouse_type: str
    responsible_employee_id: UUID | None
    allow_negative_stock: bool
    is_active: bool


class LocationCreate(BaseModel):
    organization_id: UUID
    warehouse_id: UUID
    parent_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    location_type: StorageLocationType = StorageLocationType.BIN
    barcode: str | None = None
    is_active: bool = True


class LocationUpdate(BaseModel):
    version: int
    warehouse_id: UUID | None = None
    parent_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location_type: StorageLocationType | None = None
    barcode: str | None = None
    is_active: bool | None = None


class LocationResponse(MutableEntityResponse):
    organization_id: UUID
    warehouse_id: UUID
    parent_id: UUID | None
    code: str
    name: str
    location_type: str
    barcode: str | None
    is_active: bool


class UnitCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    symbol: str = Field(min_length=1, max_length=32)
    precision: int = Field(default=0, ge=0, le=6)
    is_active: bool = True


class UnitUpdate(BaseModel):
    version: int
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    symbol: str | None = Field(default=None, min_length=1, max_length=32)
    precision: int | None = Field(default=None, ge=0, le=6)
    is_active: bool | None = None


class UnitResponse(MutableEntityResponse):
    organization_id: UUID
    code: str
    name: str
    symbol: str
    precision: int
    is_active: bool


class CategoryCreate(BaseModel):
    organization_id: UUID
    parent_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    is_active: bool = True


class CategoryUpdate(BaseModel):
    version: int
    parent_id: UUID | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    is_active: bool | None = None


class CategoryResponse(MutableEntityResponse):
    organization_id: UUID
    parent_id: UUID | None
    code: str
    name: str
    description: str | None
    is_active: bool


class ItemCreate(BaseModel):
    organization_id: UUID
    sku: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    category_id: UUID
    unit_of_measure_id: UUID
    item_type: ItemType = ItemType.COMPONENT
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    barcode: str | None = None
    internal_part_number: str | None = None
    drawing_number: str | None = None
    specifications: dict[str, Any] | None = None
    track_lots: bool = False
    track_serial_numbers: bool = False
    minimum_stock: Decimal = Decimal("0")
    maximum_stock: Decimal | None = None
    default_warehouse_id: UUID | None = None
    image_reference: str | None = None
    is_active: bool = True


class ItemUpdate(BaseModel):
    version: int
    sku: str | None = Field(default=None, min_length=1, max_length=96)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: UUID | None = None
    unit_of_measure_id: UUID | None = None
    item_type: ItemType | None = None
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    barcode: str | None = None
    internal_part_number: str | None = None
    drawing_number: str | None = None
    specifications: dict[str, Any] | None = None
    track_lots: bool | None = None
    track_serial_numbers: bool | None = None
    minimum_stock: Decimal | None = None
    maximum_stock: Decimal | None = None
    default_warehouse_id: UUID | None = None
    image_reference: str | None = None
    is_active: bool | None = None


class ItemResponse(MutableEntityResponse):
    organization_id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID
    unit_of_measure_id: UUID
    item_type: str
    manufacturer: str | None
    manufacturer_part_number: str | None
    barcode: str | None
    internal_part_number: str | None
    drawing_number: str | None
    specifications: dict[str, Any] | None
    track_lots: bool
    track_serial_numbers: bool
    minimum_stock: Decimal
    maximum_stock: Decimal | None
    default_warehouse_id: UUID | None
    image_reference: str | None
    is_active: bool


class LotCreate(BaseModel):
    organization_id: UUID
    item_id: UUID
    lot_number: str = Field(min_length=1, max_length=128)
    manufactured_at: date | None = None
    expires_at: date | None = None
    notes: str | None = None
    is_active: bool = True


class LotResponse(MutableEntityResponse):
    organization_id: UUID
    item_id: UUID
    lot_number: str
    manufactured_at: date | None
    expires_at: date | None
    notes: str | None
    is_active: bool


class SerialCreate(BaseModel):
    organization_id: UUID
    item_id: UUID
    serial_number: str = Field(min_length=1, max_length=128)
    status: SerialStatus = SerialStatus.AVAILABLE
    current_warehouse_id: UUID | None = None
    current_location_id: UUID | None = None
    lot_id: UUID | None = None
    notes: str | None = None


class SerialStatusUpdate(BaseModel):
    status: SerialStatus


class SerialResponse(MutableEntityResponse):
    organization_id: UUID
    item_id: UUID
    serial_number: str
    status: str
    current_warehouse_id: UUID | None
    current_location_id: UUID | None
    lot_id: UUID | None
    notes: str | None


class DocumentCreate(BaseModel):
    organization_id: UUID
    document_number: str | None = None
    document_type: InventoryDocumentType
    document_date: datetime | None = None
    source_warehouse_id: UUID | None = None
    destination_warehouse_id: UUID | None = None
    responsible_employee_id: UUID | None = None
    reference: str | None = None
    notes: str | None = None


class DocumentUpdate(BaseModel):
    version: int
    document_date: datetime | None = None
    source_warehouse_id: UUID | None = None
    destination_warehouse_id: UUID | None = None
    responsible_employee_id: UUID | None = None
    reference: str | None = None
    notes: str | None = None


class DocumentResponse(MutableEntityResponse):
    organization_id: UUID
    document_number: str
    document_type: str
    status: str
    document_date: datetime
    source_warehouse_id: UUID | None
    destination_warehouse_id: UUID | None
    responsible_employee_id: UUID | None
    reference: str | None
    notes: str | None
    posted_at: datetime | None
    posted_by_user_id: UUID | None
    cancelled_at: datetime | None
    cancelled_by_user_id: UUID | None
    cancellation_reason: str | None
    created_by_user_id: UUID


class DocumentLineCreate(BaseModel):
    item_id: UUID
    quantity: Decimal = Field(gt=0)
    source_location_id: UUID | None = None
    destination_location_id: UUID | None = None
    lot_id: UUID | None = None
    notes: str | None = None


class DocumentLineUpdate(DocumentLineCreate):
    version: int


class DocumentLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    line_number: int
    item_id: UUID
    quantity: Decimal
    source_location_id: UUID | None
    destination_location_id: UUID | None
    lot_id: UUID | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    version: int


class AttachSerialsPayload(BaseModel):
    serial_ids: list[UUID]


class CancelDocumentPayload(BaseModel):
    reason: str | None = None


class StockBalanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    item_id: UUID
    warehouse_id: UUID
    location_id: UUID | None
    lot_id: UUID | None
    serial_id: UUID | None
    quantity: Decimal
    updated_at: datetime


class MovementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    document_id: UUID
    document_line_id: UUID
    item_id: UUID
    warehouse_id: UUID
    location_id: UUID | None
    lot_id: UUID | None
    serial_id: UUID | None
    quantity_delta: Decimal
    occurred_at: datetime
    movement_kind: str
    reversal_of_movement_id: UUID | None
    created_by_user_id: UUID
    created_at: datetime


class UserInventoryScopeResponse(BaseModel):
    site_ids: list[UUID]
    warehouse_ids: list[UUID]


class UserInventoryScopeUpdate(UserInventoryScopeResponse):
    pass
