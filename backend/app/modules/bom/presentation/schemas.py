from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.bom.domain.entities import (
    BomLineSourceType,
    BomVersionStatus,
    SpecificationStatus,
    SpecificationType,
)


class MutableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    version: int


class SpecificationCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    product_item_id: UUID | None = None
    specification_type: SpecificationType = SpecificationType.PRODUCT
    effective_from: date | None = None
    effective_to: date | None = None
    author_employee_id: UUID | None = None
    notes: str | None = None
    is_active: bool = True


class SpecificationUpdate(BaseModel):
    version: int
    code: str | None = Field(default=None, min_length=1, max_length=96)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    product_item_id: UUID | None = None
    specification_type: SpecificationType | None = None
    effective_from: date | None = None
    effective_to: date | None = None
    author_employee_id: UUID | None = None
    notes: str | None = None
    is_active: bool | None = None


class SpecificationCopyPayload(BaseModel):
    code: str = Field(min_length=1, max_length=96)
    name: str | None = Field(default=None, min_length=1, max_length=255)


class SpecificationResponse(MutableResponse):
    organization_id: UUID
    code: str
    name: str
    description: str | None
    product_item_id: UUID | None
    specification_type: str
    status: str
    current_version_number: int
    effective_from: date | None
    effective_to: date | None
    author_employee_id: UUID | None
    approved_by_employee_id: UUID | None
    approved_at: datetime | None
    notes: str | None
    is_active: bool
    created_by_user_id: UUID


class VersionCreate(BaseModel):
    source_version_id: UUID | None = None
    version_label: str | None = Field(default=None, max_length=80)
    change_reason: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class VersionUpdate(BaseModel):
    version: int
    version_label: str | None = Field(default=None, max_length=80)
    change_reason: str | None = None
    effective_from: date | None = None
    effective_to: date | None = None


class VersionResponse(MutableResponse):
    bom_id: UUID
    version_number: int
    version_label: str | None
    status: str
    change_reason: str | None
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    effective_from: date | None
    effective_to: date | None


class LineCreate(BaseModel):
    line_number: int | None = Field(default=None, ge=1)
    parent_line_id: UUID | None = None
    inventory_item_id: UUID | None = None
    position_code: str | None = Field(default=None, max_length=96)
    display_name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    quantity: Decimal = Field(gt=0)
    unit_of_measure_id: UUID
    waste_percentage: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    is_optional: bool = False
    is_alternative: bool = False
    alternative_group: str | None = Field(default=None, max_length=80)
    reference_designator: str | None = Field(default=None, max_length=128)
    drawing_number: str | None = Field(default=None, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=255)
    manufacturer_part_number: str | None = Field(default=None, max_length=128)
    technical_requirements: str | None = None
    notes: str | None = None
    sort_order: int | None = None
    source_type: BomLineSourceType | None = None


class LineUpdate(BaseModel):
    version: int
    line_number: int | None = Field(default=None, ge=1)
    parent_line_id: UUID | None = None
    inventory_item_id: UUID | None = None
    position_code: str | None = Field(default=None, max_length=96)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_of_measure_id: UUID | None = None
    waste_percentage: Decimal | None = Field(default=None, ge=0, le=100)
    is_optional: bool | None = None
    is_alternative: bool | None = None
    alternative_group: str | None = Field(default=None, max_length=80)
    reference_designator: str | None = Field(default=None, max_length=128)
    drawing_number: str | None = Field(default=None, max_length=128)
    manufacturer: str | None = Field(default=None, max_length=255)
    manufacturer_part_number: str | None = Field(default=None, max_length=128)
    technical_requirements: str | None = None
    notes: str | None = None
    sort_order: int | None = None
    source_type: BomLineSourceType | None = None


class LineResponse(MutableResponse):
    bom_version_id: UUID
    line_number: int
    parent_line_id: UUID | None
    inventory_item_id: UUID | None
    position_code: str | None
    display_name: str
    description: str | None
    quantity: Decimal
    unit_of_measure_id: UUID
    waste_percentage: Decimal
    is_optional: bool
    is_alternative: bool
    alternative_group: str | None
    reference_designator: str | None
    drawing_number: str | None
    manufacturer: str | None
    manufacturer_part_number: str | None
    technical_requirements: str | None
    notes: str | None
    sort_order: int
    source_type: str


class ReorderPayload(BaseModel):
    line_ids: list[UUID]


class AttachmentCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    storage_key: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(min_length=1, max_length=128)
    file_size: int = Field(ge=1)
    description: str | None = None


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bom_version_id: UUID
    filename: str
    storage_key: str
    mime_type: str
    file_size: int
    description: str | None
    uploaded_by_user_id: UUID
    created_at: datetime
    deleted_at: datetime | None


class ImportPreviewResponse(BaseModel):
    valid: bool
    rows: list[dict[str, Any]]


class ImportResultResponse(ImportPreviewResponse):
    imported: int = 0


class VersionCompareResponse(BaseModel):
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]


SpecificationStatusType = SpecificationStatus
VersionStatusType = BomVersionStatus
