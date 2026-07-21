from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.production.domain.entities import (
    ProductionOrderPriority,
    ProductionOrderStatus,
    ProductionOrderType,
)


class MutableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    version: int


class ProductionOrderCreate(BaseModel):
    organization_id: UUID
    order_number: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    product_item_id: UUID
    bom_version_id: UUID
    order_type: ProductionOrderType = ProductionOrderType.STANDARD
    status: ProductionOrderStatus = ProductionOrderStatus.DRAFT
    priority: ProductionOrderPriority = ProductionOrderPriority.NORMAL
    site_id: UUID
    department_id: UUID | None = None
    production_warehouse_id: UUID | None = None
    material_warehouse_id: UUID
    finished_goods_warehouse_id: UUID
    planned_quantity: Decimal = Field(gt=0)
    unit_of_measure_id: UUID | None = None
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    responsible_employee_id: UUID | None = None
    production_manager_employee_id: UUID | None = None
    notes: str | None = None


class ProductionOrderUpdate(BaseModel):
    version: int
    name: str | None = Field(default=None, max_length=255)
    priority: ProductionOrderPriority | None = None
    site_id: UUID | None = None
    department_id: UUID | None = None
    production_warehouse_id: UUID | None = None
    material_warehouse_id: UUID | None = None
    finished_goods_warehouse_id: UUID | None = None
    planned_start_date: datetime | None = None
    planned_end_date: datetime | None = None
    responsible_employee_id: UUID | None = None
    production_manager_employee_id: UUID | None = None
    notes: str | None = None


class ProductionOrderResponse(MutableResponse):
    organization_id: UUID
    order_number: str
    name: str
    product_item_id: UUID
    bom_id: UUID
    bom_version_id: UUID
    bom_version_number: int
    order_type: str
    status: str
    priority: str
    site_id: UUID
    department_id: UUID | None
    production_warehouse_id: UUID | None
    material_warehouse_id: UUID
    finished_goods_warehouse_id: UUID
    planned_quantity: Decimal
    completed_quantity: Decimal
    rejected_quantity: Decimal
    unit_of_measure_id: UUID
    planned_start_date: datetime | None
    planned_end_date: datetime | None
    actual_start_date: datetime | None
    actual_end_date: datetime | None
    responsible_employee_id: UUID | None
    production_manager_employee_id: UUID | None
    notes: str | None
    suspension_reason: str | None
    cancellation_reason: str | None
    released_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    is_active: bool


class TransitionPayload(BaseModel):
    reason: str | None = None


class RequirementAvailabilityResponse(BaseModel):
    id: UUID
    line_number: int
    inventory_item_id: UUID | None
    item_code_snapshot: str | None
    display_name: str
    planned_quantity: Decimal
    reserved_quantity: Decimal
    issued_quantity: Decimal
    returned_quantity: Decimal
    consumed_quantity: Decimal
    scrapped_quantity: Decimal
    unit_name_snapshot: str
    unit_symbol_snapshot: str
    source_type: str
    is_optional: bool
    is_alternative: bool
    available_quantity: Decimal
    shortage_quantity: Decimal
    remaining_to_issue: Decimal


class MaterialLinePayload(BaseModel):
    material_requirement_id: UUID
    quantity: Decimal = Field(gt=0)
    location_id: UUID | None = None
    lot_id: UUID | None = None
    serial_id: UUID | None = None
    notes: str | None = None
    activate_optional: bool = False


class MaterialOperationPayload(BaseModel):
    lines: list[MaterialLinePayload]
    reason: str | None = None
    notes: str | None = None
    allow_overissue: bool = False


class StageTemplateCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_sequence: int = 10
    default_department_id: UUID | None = None
    is_active: bool = True


class StageTemplateResponse(MutableResponse):
    organization_id: UUID
    code: str
    name: str
    description: str | None
    default_sequence: int
    default_department_id: UUID | None
    is_active: bool


class OrderStageCreate(BaseModel):
    stage_template_id: UUID | None = None
    sequence: int = Field(ge=1)
    code_snapshot: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    department_id: UUID | None = None
    workplace_id: UUID | None = None
    responsible_employee_id: UUID | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None


class OrderStageResponse(MutableResponse):
    production_order_id: UUID
    stage_template_id: UUID | None
    sequence: int
    code_snapshot: str | None
    name: str
    description: str | None
    status: str
    department_id: UUID | None
    workplace_id: UUID | None
    responsible_employee_id: UUID | None
    planned_start_at: datetime | None
    planned_end_at: datetime | None
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    progress_percent: int
    blocked_reason: str | None
    completion_notes: str | None


class StageTransitionPayload(BaseModel):
    status: str
    reason: str | None = None
    notes: str | None = None


class CompletionCreate(BaseModel):
    quantity_completed: Decimal = Field(gt=0)
    quantity_rejected: Decimal = Field(default=Decimal("0"), ge=0)
    destination_warehouse_id: UUID | None = None
    destination_location_id: UUID | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    completed_by_employee_id: UUID | None = None
    notes: str | None = None


class CompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_order_id: UUID
    completion_number: int
    quantity_completed: Decimal
    quantity_rejected: Decimal
    destination_warehouse_id: UUID
    destination_location_id: UUID | None
    inventory_document_id: UUID
    notes: str | None
    completed_by_employee_id: UUID | None
    created_by_user_id: UUID
    posted_at: datetime
    created_at: datetime


class DashboardResponse(BaseModel):
    active_orders: int
    planned: int
    in_progress: int
    partially_completed: int
    overdue: int
    with_material_shortage: int
    completed_today: int
    urgent_orders: list[dict[str, Any]]
    active_order_rows: list[dict[str, Any]]
