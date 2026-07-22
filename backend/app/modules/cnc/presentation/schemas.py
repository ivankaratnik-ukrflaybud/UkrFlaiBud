from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.cnc.domain.entities import (
    CncFileType,
    CncMachineStatus,
    CncMachineType,
    CncPriority,
    CncProgramStatus,
    CncSheetPlanStatus,
    CncToolType,
    CncWorkOrderStatus,
)


class MutableResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    version: int


class VersionedUpdate(BaseModel):
    version: int | None = None


class CncMachineCreate(BaseModel):
    organization_id: UUID
    site_id: UUID
    department_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    machine_type: CncMachineType = CncMachineType.ROUTER
    manufacturer: str | None = None
    model: str | None = None
    serial_number: str | None = None
    controller: str | None = None
    working_area_x_mm: Decimal | None = None
    working_area_y_mm: Decimal | None = None
    working_area_z_mm: Decimal | None = None
    max_spindle_speed_rpm: int | None = None
    max_feed_rate_mm_min: Decimal | None = None
    supported_materials: dict[str, Any] | None = None
    capabilities: dict[str, Any] | None = None
    status: CncMachineStatus = CncMachineStatus.AVAILABLE
    current_operator_employee_id: UUID | None = None
    is_active: bool = True


class CncMachineUpdate(VersionedUpdate):
    site_id: UUID | None = None
    department_id: UUID | None = None
    code: str | None = Field(default=None, max_length=64)
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: CncMachineStatus | None = None
    current_operator_employee_id: UUID | None = None
    is_active: bool | None = None


class CncMachineResponse(MutableResponse, CncMachineCreate):
    deleted_at: datetime | None = None


class StatusPayload(BaseModel):
    status: str
    reason: str | None = None


class CncToolCreate(BaseModel):
    organization_id: UUID
    inventory_item_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    tool_type: CncToolType = CncToolType.OTHER
    diameter_mm: Decimal | None = None
    working_length_mm: Decimal | None = None
    shank_diameter_mm: Decimal | None = None
    material: str | None = None
    manufacturer: str | None = None
    manufacturer_part_number: str | None = None
    expected_life_minutes: int | None = None
    is_active: bool = True


class CncToolUpdate(VersionedUpdate):
    code: str | None = None
    name: str | None = None
    tool_type: CncToolType | None = None
    is_active: bool | None = None


class CncToolResponse(MutableResponse, CncToolCreate):
    deleted_at: datetime | None = None


class CncProgramCreate(BaseModel):
    organization_id: UUID
    code: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=255)
    revision: str = Field(min_length=1, max_length=64)
    description: str | None = None
    machine_type: CncMachineType | None = None
    compatible_machine_ids: list[str] | None = None
    source_file_name: str | None = None
    storage_key: str | None = None
    file_type: CncFileType = CncFileType.OTHER
    checksum: str | None = None
    program_status: CncProgramStatus = CncProgramStatus.DRAFT
    estimated_runtime_minutes: Decimal | None = None
    notes: str | None = None


class CncProgramUpdate(VersionedUpdate):
    code: str | None = None
    name: str | None = None
    revision: str | None = None
    description: str | None = None
    machine_type: CncMachineType | None = None
    compatible_machine_ids: list[str] | None = None
    source_file_name: str | None = None
    storage_key: str | None = None
    file_type: CncFileType | None = None
    checksum: str | None = None
    program_status: CncProgramStatus | None = None
    estimated_runtime_minutes: Decimal | None = None
    notes: str | None = None


class CncProgramResponse(MutableResponse, CncProgramCreate):
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    deleted_at: datetime | None = None


class CncPartCreate(BaseModel):
    organization_id: UUID
    inventory_item_id: UUID | None = None
    code: str = Field(min_length=1, max_length=96)
    name: str = Field(min_length=1, max_length=255)
    drawing_number: str | None = None
    drawing_revision: str | None = None
    description: str | None = None
    material_item_id: UUID | None = None
    material_name_snapshot: str | None = None
    thickness_mm: Decimal | None = None
    finished_length_mm: Decimal | None = None
    finished_width_mm: Decimal | None = None
    finished_height_mm: Decimal | None = None
    default_program_id: UUID | None = None
    default_machine_id: UUID | None = None
    default_quantity_per_sheet: Decimal | None = None
    estimated_setup_minutes: Decimal | None = None
    estimated_cycle_minutes: Decimal | None = None
    technical_requirements: str | None = None
    quality_requirements: str | None = None
    is_active: bool = True


class CncPartUpdate(VersionedUpdate):
    code: str | None = None
    name: str | None = None
    drawing_number: str | None = None
    drawing_revision: str | None = None
    description: str | None = None
    material_item_id: UUID | None = None
    material_name_snapshot: str | None = None
    is_active: bool | None = None


class CncPartResponse(MutableResponse, CncPartCreate):
    deleted_at: datetime | None = None


class CncSheetPlanCreate(BaseModel):
    organization_id: UUID
    plan_number: str
    name: str
    status: CncSheetPlanStatus = CncSheetPlanStatus.DRAFT
    material_item_id: UUID
    material_name_snapshot: str | None = None
    sheet_length_mm: Decimal = Field(gt=0)
    sheet_width_mm: Decimal = Field(gt=0)
    thickness_mm: Decimal = Field(gt=0)
    planned_sheet_quantity: Decimal = Field(gt=0)
    actual_sheet_quantity: Decimal = Decimal("0")
    estimated_utilization_percent: Decimal | None = Field(default=None, ge=0, le=100)
    actual_utilization_percent: Decimal | None = Field(default=None, ge=0, le=100)
    program_id: UUID | None = None
    machine_id: UUID | None = None
    production_order_id: UUID | None = None
    notes: str | None = None


class CncSheetPlanUpdate(VersionedUpdate):
    name: str | None = None
    status: CncSheetPlanStatus | None = None
    actual_sheet_quantity: Decimal | None = None
    estimated_utilization_percent: Decimal | None = None
    actual_utilization_percent: Decimal | None = None
    notes: str | None = None


class CncSheetPlanResponse(MutableResponse, CncSheetPlanCreate):
    material_name_snapshot: str
    created_by_user_id: UUID
    approved_by_user_id: UUID | None
    approved_at: datetime | None
    deleted_at: datetime | None = None


class CncSheetPlanLineCreate(BaseModel):
    cnc_part_id: UUID
    quantity_per_sheet: Decimal = Field(gt=0)
    total_planned_quantity: Decimal | None = Field(default=None, gt=0)
    sort_order: int = 10
    notes: str | None = None


class CncSheetPlanLineUpdate(VersionedUpdate):
    quantity_per_sheet: Decimal | None = Field(default=None, gt=0)
    total_planned_quantity: Decimal | None = Field(default=None, gt=0)
    sort_order: int | None = None
    notes: str | None = None


class CncSheetPlanLineResponse(MutableResponse):
    sheet_plan_id: UUID
    cnc_part_id: UUID
    part_code_snapshot: str
    part_name_snapshot: str
    drawing_revision_snapshot: str | None
    quantity_per_sheet: Decimal
    total_planned_quantity: Decimal
    sort_order: int
    notes: str | None


class CncWorkOrderCreate(BaseModel):
    organization_id: UUID
    work_order_number: str | None = None
    name: str | None = None
    production_order_id: UUID | None = None
    production_stage_id: UUID | None = None
    sheet_plan_id: UUID | None = None
    cnc_part_id: UUID | None = None
    program_id: UUID | None = None
    machine_id: UUID | None = None
    site_id: UUID
    department_id: UUID | None = None
    source_warehouse_id: UUID
    output_warehouse_id: UUID
    status: CncWorkOrderStatus = CncWorkOrderStatus.DRAFT
    priority: CncPriority = CncPriority.NORMAL
    planned_quantity: Decimal = Field(gt=0)
    unit_of_measure_id: UUID
    material_item_id: UUID | None = None
    planned_material_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    planned_setup_minutes: Decimal | None = None
    planned_cycle_minutes: Decimal | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    operator_employee_id: UUID | None = None
    responsible_employee_id: UUID | None = None
    notes: str | None = None


class CncWorkOrderUpdate(VersionedUpdate):
    name: str | None = None
    priority: CncPriority | None = None
    machine_id: UUID | None = None
    program_id: UUID | None = None
    operator_employee_id: UUID | None = None
    responsible_employee_id: UUID | None = None
    planned_start_at: datetime | None = None
    planned_end_at: datetime | None = None
    notes: str | None = None


class CncWorkOrderResponse(MutableResponse, CncWorkOrderCreate):
    work_order_number: str
    name: str
    completed_quantity: Decimal
    rejected_quantity: Decimal
    issued_material_quantity: Decimal
    returned_material_quantity: Decimal
    scrapped_material_quantity: Decimal
    actual_setup_minutes: Decimal
    actual_cycle_minutes: Decimal
    actual_start_at: datetime | None
    actual_end_at: datetime | None
    blocked_reason: str | None
    cancellation_reason: str | None
    created_by_user_id: UUID
    part_code_snapshot: str | None
    part_name_snapshot: str | None
    drawing_revision_snapshot: str | None
    program_revision_snapshot: str | None
    queue_position: int | None
    deleted_at: datetime | None = None


class CncOutputResponse(MutableResponse):
    work_order_id: UUID
    cnc_part_id: UUID | None
    inventory_item_id: UUID | None
    part_code_snapshot: str
    part_name_snapshot: str
    drawing_revision_snapshot: str | None
    planned_quantity: Decimal
    completed_quantity: Decimal
    rejected_quantity: Decimal
    unit_of_measure_id: UUID
    output_inventory_document_id: UUID | None


class MaterialPayload(BaseModel):
    quantity: Decimal = Field(gt=0)
    location_id: UUID | None = None
    lot_id: UUID | None = None
    reason: str | None = None
    notes: str | None = None
    allow_overissue: bool = False


class MaterialTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_order_id: UUID
    transaction_type: str
    inventory_document_id: UUID
    material_item_id: UUID
    warehouse_id: UUID
    location_id: UUID | None
    lot_id: UUID | None
    quantity: Decimal
    reason: str | None
    posted_at: datetime
    created_at: datetime


class ReportOutputPayload(BaseModel):
    output_id: UUID | None = None
    good_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    rejected_quantity: Decimal = Field(default=Decimal("0"), ge=0)
    rejection_reason: str | None = None
    notes: str | None = None
    allow_overproduction: bool = False


class RegisterOffcutPayload(BaseModel):
    material_item_id: UUID | None = None
    offcut_code: str
    length_mm: Decimal = Field(gt=0)
    width_mm: Decimal = Field(gt=0)
    thickness_mm: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    warehouse_id: UUID
    location_id: UUID | None = None
    notes: str | None = None


class CncOffcutResponse(MutableResponse, RegisterOffcutPayload):
    organization_id: UUID
    source_work_order_id: UUID
    material_item_id: UUID
    status: str
    deleted_at: datetime | None = None


class ReorderPayload(BaseModel):
    machine_id: UUID
    ordered_work_order_ids: list[UUID]


class ChangeMachinePayload(BaseModel):
    machine_id: UUID


class CopySheetPlanPayload(BaseModel):
    plan_number: str


class DashboardResponse(BaseModel):
    running_machines: int
    available_machines: int
    queued_work_orders: int
    running_work_orders: int
    blocked_work_orders: int
    overdue_work_orders: int
    completed_today: int
    rejected_today: Decimal
