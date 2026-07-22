from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from app.modules.cnc.domain.entities import (
    CncExecutionEventType,
    CncFileType,
    CncMachineStatus,
    CncMachineType,
    CncMaterialTransactionType,
    CncOffcutStatus,
    CncPriority,
    CncProgramStatus,
    CncSheetPlanStatus,
    CncToolType,
    CncWorkOrderStatus,
)


def _values(enum_type: type[StrEnum]) -> str:
    return ", ".join(f"'{item.value}'" for item in enum_type)


class CncMachineModel(EntityMixin, Base):
    __tablename__ = "cnc_machines"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cnc_machines_organization_code"),
        CheckConstraint(
            f"machine_type IN ({_values(CncMachineType)})", name="ck_cnc_machines_type"
        ),
        CheckConstraint(f"status IN ({_values(CncMachineStatus)})", name="ck_cnc_machines_status"),
        Index("ix_cnc_machines_organization_id", "organization_id"),
        Index("ix_cnc_machines_site_id", "site_id"),
        Index("ix_cnc_machines_status", "status"),
        Index("ix_cnc_machines_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_sites.id", ondelete="RESTRICT")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    machine_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncMachineType.ROUTER.value
    )
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    model: Mapped[str | None] = mapped_column(String(255))
    serial_number: Mapped[str | None] = mapped_column(String(128))
    controller: Mapped[str | None] = mapped_column(String(128))
    working_area_x_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    working_area_y_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    working_area_z_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    max_spindle_speed_rpm: Mapped[int | None] = mapped_column(Integer)
    max_feed_rate_mm_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    supported_materials: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    capabilities: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncMachineStatus.AVAILABLE.value
    )
    current_operator_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CncToolModel(EntityMixin, Base):
    __tablename__ = "cnc_tools"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cnc_tools_organization_code"),
        CheckConstraint(f"tool_type IN ({_values(CncToolType)})", name="ck_cnc_tools_type"),
        Index("ix_cnc_tools_organization_id", "organization_id"),
        Index("ix_cnc_tools_item_id", "inventory_item_id"),
        Index("ix_cnc_tools_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(32), nullable=False)
    diameter_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    working_length_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    shank_diameter_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    material: Mapped[str | None] = mapped_column(String(128))
    manufacturer: Mapped[str | None] = mapped_column(String(255))
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(128))
    expected_life_minutes: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CncProgramModel(EntityMixin, Base):
    __tablename__ = "cnc_programs"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", "revision", name="uq_cnc_programs_code_revision"
        ),
        CheckConstraint(
            f"machine_type IS NULL OR machine_type IN ({_values(CncMachineType)})",
            name="ck_cnc_programs_machine_type",
        ),
        CheckConstraint(f"file_type IN ({_values(CncFileType)})", name="ck_cnc_programs_file_type"),
        CheckConstraint(
            f"program_status IN ({_values(CncProgramStatus)})",
            name="ck_cnc_programs_status",
        ),
        Index("ix_cnc_programs_organization_id", "organization_id"),
        Index("ix_cnc_programs_code", "code"),
        Index("ix_cnc_programs_status", "program_status"),
        Index(
            "ix_cnc_programs_checksum",
            "organization_id",
            "checksum",
            postgresql_where=text("checksum IS NOT NULL"),
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    revision: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    machine_type: Mapped[str | None] = mapped_column(String(32))
    compatible_machine_ids: Mapped[list[str] | None] = mapped_column(JSONB)
    source_file_name: Mapped[str | None] = mapped_column(String(255))
    storage_key: Mapped[str | None] = mapped_column(String(512))
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    program_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncProgramStatus.DRAFT.value
    )
    estimated_runtime_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class CncPartModel(EntityMixin, Base):
    __tablename__ = "cnc_parts"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_cnc_parts_organization_code"),
        Index("ix_cnc_parts_organization_id", "organization_id"),
        Index("ix_cnc_parts_item_id", "inventory_item_id"),
        Index("ix_cnc_parts_material_item_id", "material_item_id"),
        Index("ix_cnc_parts_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    drawing_number: Mapped[str | None] = mapped_column(String(128))
    drawing_revision: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    material_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    material_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    thickness_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    finished_length_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    finished_width_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    finished_height_mm: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    default_program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_programs.id", ondelete="SET NULL")
    )
    default_machine_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_machines.id", ondelete="SET NULL")
    )
    default_quantity_per_sheet: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    estimated_setup_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    estimated_cycle_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    technical_requirements: Mapped[str | None] = mapped_column(Text)
    quality_requirements: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CncSheetPlanModel(EntityMixin, Base):
    __tablename__ = "cnc_sheet_plans"
    __table_args__ = (
        UniqueConstraint("organization_id", "plan_number", name="uq_cnc_sheet_plans_number"),
        CheckConstraint(f"status IN ({_values(CncSheetPlanStatus)})", name="ck_cnc_sheet_status"),
        CheckConstraint("planned_sheet_quantity > 0", name="ck_cnc_sheet_planned_qty"),
        CheckConstraint("actual_sheet_quantity >= 0", name="ck_cnc_sheet_actual_qty"),
        CheckConstraint(
            "estimated_utilization_percent IS NULL OR "
            "(estimated_utilization_percent >= 0 AND estimated_utilization_percent <= 100)",
            name="ck_cnc_sheet_estimated_utilization",
        ),
        CheckConstraint(
            "actual_utilization_percent IS NULL OR "
            "(actual_utilization_percent >= 0 AND actual_utilization_percent <= 100)",
            name="ck_cnc_sheet_actual_utilization",
        ),
        Index("ix_cnc_sheet_plans_organization_id", "organization_id"),
        Index("ix_cnc_sheet_plans_status", "status"),
        Index("ix_cnc_sheet_plans_material", "material_item_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    plan_number: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncSheetPlanStatus.DRAFT.value
    )
    material_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    material_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    sheet_length_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sheet_width_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    thickness_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    planned_sheet_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    actual_sheet_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0
    )
    estimated_utilization_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    actual_utilization_percent: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_programs.id", ondelete="SET NULL")
    )
    machine_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_machines.id", ondelete="SET NULL")
    )
    production_order_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CncSheetPlanLineModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "cnc_sheet_plan_lines"
    __table_args__ = (
        CheckConstraint("quantity_per_sheet > 0", name="ck_cnc_sheet_lines_qty_per_sheet"),
        CheckConstraint("total_planned_quantity > 0", name="ck_cnc_sheet_lines_total_qty"),
        Index("ix_cnc_sheet_plan_lines_plan", "sheet_plan_id"),
        Index("ix_cnc_sheet_plan_lines_part", "cnc_part_id"),
    )

    sheet_plan_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_sheet_plans.id", ondelete="CASCADE")
    )
    cnc_part_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_parts.id", ondelete="RESTRICT")
    )
    part_code_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    part_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    drawing_revision_snapshot: Mapped[str | None] = mapped_column(String(64))
    quantity_per_sheet: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    total_planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    notes: Mapped[str | None] = mapped_column(Text)


class CncWorkOrderModel(EntityMixin, Base):
    __tablename__ = "cnc_work_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "work_order_number", name="uq_cnc_work_orders_number"),
        CheckConstraint(f"status IN ({_values(CncWorkOrderStatus)})", name="ck_cnc_work_status"),
        CheckConstraint(f"priority IN ({_values(CncPriority)})", name="ck_cnc_work_priority"),
        CheckConstraint("planned_quantity > 0", name="ck_cnc_work_planned_qty"),
        CheckConstraint("completed_quantity >= 0", name="ck_cnc_work_completed_qty"),
        CheckConstraint("rejected_quantity >= 0", name="ck_cnc_work_rejected_qty"),
        CheckConstraint("planned_material_quantity >= 0", name="ck_cnc_work_planned_material"),
        CheckConstraint("issued_material_quantity >= 0", name="ck_cnc_work_issued_material"),
        CheckConstraint("returned_material_quantity >= 0", name="ck_cnc_work_returned_material"),
        CheckConstraint("scrapped_material_quantity >= 0", name="ck_cnc_work_scrapped_material"),
        CheckConstraint("actual_setup_minutes >= 0", name="ck_cnc_work_actual_setup"),
        CheckConstraint("actual_cycle_minutes >= 0", name="ck_cnc_work_actual_cycle"),
        Index("ix_cnc_work_orders_organization_id", "organization_id"),
        Index("ix_cnc_work_orders_status", "status"),
        Index("ix_cnc_work_orders_machine", "machine_id"),
        Index("ix_cnc_work_orders_site", "site_id"),
        Index("ix_cnc_work_orders_production", "production_order_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    work_order_number: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    production_order_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="SET NULL")
    )
    production_stage_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_order_stages.id", ondelete="SET NULL")
    )
    sheet_plan_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_sheet_plans.id", ondelete="SET NULL")
    )
    cnc_part_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_parts.id", ondelete="SET NULL")
    )
    program_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_programs.id", ondelete="SET NULL")
    )
    part_code_snapshot: Mapped[str | None] = mapped_column(String(96))
    part_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    drawing_revision_snapshot: Mapped[str | None] = mapped_column(String(64))
    program_revision_snapshot: Mapped[str | None] = mapped_column(String(64))
    machine_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_machines.id", ondelete="SET NULL")
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_sites.id", ondelete="RESTRICT")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    source_warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    output_warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncWorkOrderStatus.DRAFT.value
    )
    priority: Mapped[str] = mapped_column(String(32), nullable=False, default=CncPriority.NORMAL)
    queue_position: Mapped[int | None] = mapped_column(Integer)
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    completed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    material_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    material_name_snapshot: Mapped[str | None] = mapped_column(String(255))
    planned_material_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0
    )
    issued_material_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0
    )
    returned_material_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0
    )
    scrapped_material_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0
    )
    planned_setup_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    planned_cycle_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    actual_setup_minutes: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    actual_cycle_minutes: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    operator_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    responsible_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    cancellation_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class CncWorkOrderOutputModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "cnc_work_order_outputs"
    __table_args__ = (
        CheckConstraint("planned_quantity >= 0", name="ck_cnc_outputs_planned"),
        CheckConstraint("completed_quantity >= 0", name="ck_cnc_outputs_completed"),
        CheckConstraint("rejected_quantity >= 0", name="ck_cnc_outputs_rejected"),
        Index("ix_cnc_outputs_work_order", "work_order_id"),
    )

    work_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_work_orders.id", ondelete="CASCADE")
    )
    cnc_part_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_parts.id", ondelete="SET NULL")
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="SET NULL")
    )
    part_code_snapshot: Mapped[str] = mapped_column(String(96), nullable=False)
    part_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    drawing_revision_snapshot: Mapped[str | None] = mapped_column(String(64))
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    completed_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    rejected_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0)
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    output_inventory_document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="SET NULL")
    )


class CncExecutionLogModel(Base):
    __tablename__ = "cnc_execution_logs"
    __table_args__ = (
        CheckConstraint(
            f"event_type IN ({_values(CncExecutionEventType)})", name="ck_cnc_execution_event_type"
        ),
        Index("ix_cnc_execution_logs_work_order", "work_order_id"),
        Index("ix_cnc_execution_logs_machine", "machine_id"),
        Index("ix_cnc_execution_logs_event_at", "event_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_work_orders.id", ondelete="CASCADE")
    )
    machine_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_machines.id", ondelete="RESTRICT")
    )
    operator_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    duration_minutes: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quantity_good: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    quantity_rejected: Mapped[Decimal | None] = mapped_column(Numeric(18, 6))
    reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CncMaterialTransactionModel(Base):
    __tablename__ = "cnc_material_transactions"
    __table_args__ = (
        CheckConstraint(
            f"transaction_type IN ({_values(CncMaterialTransactionType)})",
            name="ck_cnc_material_transactions_type",
        ),
        CheckConstraint("quantity > 0", name="ck_cnc_material_transactions_quantity"),
        Index("ix_cnc_material_transactions_work_order", "work_order_id"),
        Index("ix_cnc_material_transactions_document", "inventory_document_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    work_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_work_orders.id", ondelete="CASCADE")
    )
    transaction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    inventory_document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="RESTRICT")
    )
    material_item_id: Mapped[UUID] = mapped_column(
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
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CncOffcutModel(EntityMixin, Base):
    __tablename__ = "cnc_offcuts"
    __table_args__ = (
        UniqueConstraint("organization_id", "offcut_code", name="uq_cnc_offcuts_code"),
        CheckConstraint(f"status IN ({_values(CncOffcutStatus)})", name="ck_cnc_offcuts_status"),
        CheckConstraint("length_mm > 0", name="ck_cnc_offcuts_length"),
        CheckConstraint("width_mm > 0", name="ck_cnc_offcuts_width"),
        CheckConstraint("thickness_mm > 0", name="ck_cnc_offcuts_thickness"),
        CheckConstraint("quantity > 0", name="ck_cnc_offcuts_quantity"),
        Index("ix_cnc_offcuts_organization_id", "organization_id"),
        Index("ix_cnc_offcuts_material", "material_item_id"),
        Index("ix_cnc_offcuts_status", "status"),
        Index("ix_cnc_offcuts_warehouse", "warehouse_id"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    source_work_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_work_orders.id", ondelete="RESTRICT")
    )
    material_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    offcut_code: Mapped[str] = mapped_column(String(96), nullable=False)
    length_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    width_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    thickness_mm: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default=CncOffcutStatus.AVAILABLE.value
    )
    notes: Mapped[str | None] = mapped_column(Text)


class CncWorkOrderCommentModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "cnc_work_order_comments"
    __table_args__ = (Index("ix_cnc_work_order_comments_order", "work_order_id"),)

    work_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("cnc_work_orders.id", ondelete="CASCADE")
    )
    author_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
