from datetime import datetime
from decimal import Decimal
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import EntityMixin, IdMixin, TimestampMixin, VersionMixin
from app.modules.production.domain.entities import (
    ProductionMaterialSourceType,
    ProductionMaterialTransactionStatus,
    ProductionMaterialTransactionType,
    ProductionOrderPriority,
    ProductionOrderStatus,
    ProductionOrderType,
    ProductionStageStatus,
)


class ProductionOrderModel(EntityMixin, Base):
    __tablename__ = "production_orders"
    __table_args__ = (
        UniqueConstraint("organization_id", "order_number", name="uq_production_orders_number"),
        CheckConstraint(
            "order_type IN ('standard', 'prototype', 'repair', 'rework', 'kit', 'other')",
            name="ck_production_orders_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'planned', 'released', 'materials_reserved', 'in_progress', "
            "'partially_completed', 'completed', 'suspended', 'cancelled')",
            name="ck_production_orders_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'normal', 'high', 'urgent')",
            name="ck_production_orders_priority",
        ),
        CheckConstraint("planned_quantity > 0", name="ck_production_orders_planned_qty"),
        CheckConstraint("completed_quantity >= 0", name="ck_production_orders_completed_qty"),
        CheckConstraint("rejected_quantity >= 0", name="ck_production_orders_rejected_qty"),
        Index("ix_production_orders_organization_id", "organization_id"),
        Index("ix_production_orders_number", "order_number"),
        Index("ix_production_orders_status", "status"),
        Index("ix_production_orders_site_id", "site_id"),
        Index("ix_production_orders_product_item_id", "product_item_id"),
        Index("ix_production_orders_planned_start", "planned_start_date"),
        Index("ix_production_orders_planned_end", "planned_end_date"),
        Index("ix_production_orders_responsible", "responsible_employee_id"),
        Index("ix_production_orders_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    order_number: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    bom_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_specifications.id", ondelete="RESTRICT")
    )
    bom_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_versions.id", ondelete="RESTRICT")
    )
    bom_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    order_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionOrderType.STANDARD.value,
        server_default=ProductionOrderType.STANDARD.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionOrderStatus.DRAFT.value,
        server_default=ProductionOrderStatus.DRAFT.value,
    )
    priority: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionOrderPriority.NORMAL.value,
        server_default=ProductionOrderPriority.NORMAL.value,
    )
    site_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_sites.id", ondelete="RESTRICT")
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    production_warehouse_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    material_warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    finished_goods_warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    completed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    rejected_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    planned_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    planned_end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    actual_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    responsible_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    production_manager_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    suspension_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ProductionOrderBomSnapshotModel(Base):
    __tablename__ = "production_order_bom_snapshots"
    __table_args__ = (Index("ix_production_snapshots_order_id", "production_order_id"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    source_bom_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_specifications.id", ondelete="RESTRICT")
    )
    source_bom_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_versions.id", ondelete="RESTRICT")
    )
    source_bom_version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    specification_code: Mapped[str] = mapped_column(String(96), nullable=False)
    specification_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str | None] = mapped_column(String(96), nullable=True)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_name: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductionMaterialRequirementModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "production_material_requirements"
    __table_args__ = (
        UniqueConstraint(
            "production_order_id", "line_number", name="uq_production_requirements_line"
        ),
        CheckConstraint("required_quantity_per_unit > 0", name="ck_prod_req_per_unit_positive"),
        CheckConstraint("waste_percentage >= 0", name="ck_prod_req_waste_nonnegative"),
        CheckConstraint("planned_quantity >= 0", name="ck_prod_req_planned_nonnegative"),
        CheckConstraint("reserved_quantity >= 0", name="ck_prod_req_reserved_nonnegative"),
        CheckConstraint("issued_quantity >= 0", name="ck_prod_req_issued_nonnegative"),
        CheckConstraint("returned_quantity >= 0", name="ck_prod_req_returned_nonnegative"),
        CheckConstraint("consumed_quantity >= 0", name="ck_prod_req_consumed_nonnegative"),
        CheckConstraint("scrapped_quantity >= 0", name="ck_prod_req_scrapped_nonnegative"),
        CheckConstraint(
            "source_type IN ('inventory_item', 'manual', 'subassembly')",
            name="ck_prod_req_source_type",
        ),
        Index("ix_production_requirements_order_id", "production_order_id"),
        Index("ix_production_requirements_item_id", "inventory_item_id"),
    )

    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    source_bom_line_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_lines.id", ondelete="SET NULL")
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_requirement_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_material_requirements.id")
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    item_code_snapshot: Mapped[str | None] = mapped_column(String(96), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_quantity_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    waste_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    planned_quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    reserved_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    issued_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    returned_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    consumed_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    scrapped_quantity: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    unit_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    unit_symbol_snapshot: Mapped[str] = mapped_column(String(32), nullable=False)
    is_optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_alternative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    alternative_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionMaterialSourceType.MANUAL.value,
        server_default=ProductionMaterialSourceType.MANUAL.value,
    )
    technical_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductionMaterialReservationModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "production_material_reservations"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_production_reservations_quantity"),
        CheckConstraint(
            "status IN ('active', 'released')", name="ck_production_reservations_status"
        ),
        Index("ix_production_reservations_order_id", "production_order_id"),
        Index("ix_production_reservations_requirement_id", "material_requirement_id"),
        Index("ix_production_reservations_item_warehouse", "inventory_item_id", "warehouse_id"),
        Index("ix_production_reservations_status", "status"),
    )

    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    material_requirement_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_material_requirements.id", ondelete="CASCADE"),
    )
    inventory_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class ProductionStageTemplateModel(EntityMixin, Base):
    __tablename__ = "production_stage_templates"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_production_stage_templates_code"),
        Index("ix_production_stage_templates_org", "organization_id"),
        Index("ix_production_stage_templates_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    default_department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class ProductionOrderStageModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "production_order_stages"
    __table_args__ = (
        UniqueConstraint("production_order_id", "sequence", name="uq_production_order_stage_seq"),
        CheckConstraint(
            "status IN ('pending', 'ready', 'in_progress', 'blocked', 'completed', "
            "'skipped', 'cancelled')",
            name="ck_production_order_stages_status",
        ),
        CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100",
            name="ck_production_stage_progress",
        ),
        Index("ix_production_order_stages_order", "production_order_id"),
        Index("ix_production_order_stages_status", "status"),
    )

    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    stage_template_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_stage_templates.id", ondelete="SET NULL")
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    code_snapshot: Mapped[str | None] = mapped_column(String(64), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionStageStatus.PENDING.value,
        server_default=ProductionStageStatus.PENDING.value,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("departments.id", ondelete="SET NULL")
    )
    workplace_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    responsible_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planned_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    actual_end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    progress_percent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class ProductionMaterialTransactionModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "production_material_transactions"
    __table_args__ = (
        CheckConstraint(
            "transaction_type IN ('reservation', 'reservation_release', 'issue', 'return', "
            "'consumption', 'scrap', 'correction')",
            name="ck_production_material_transactions_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'posted', 'cancelled')",
            name="ck_production_material_transactions_status",
        ),
        Index("ix_production_material_transactions_order", "production_order_id"),
        Index("ix_production_material_transactions_created", "created_at"),
    )

    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    transaction_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ProductionMaterialTransactionType.ISSUE.value
    )
    inventory_document_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=ProductionMaterialTransactionStatus.POSTED.value,
        server_default=ProductionMaterialTransactionStatus.POSTED.value,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    posted_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductionMaterialTransactionLineModel(Base):
    __tablename__ = "production_material_transaction_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_production_material_tx_lines_quantity"),
        Index("ix_production_material_tx_lines_transaction", "transaction_id"),
        Index("ix_production_material_tx_lines_requirement", "material_requirement_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_material_transactions.id", ondelete="CASCADE"),
    )
    material_requirement_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("production_material_requirements.id", ondelete="RESTRICT"),
    )
    inventory_item_id: Mapped[UUID] = mapped_column(
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
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductionCompletionModel(Base):
    __tablename__ = "production_completions"
    __table_args__ = (
        UniqueConstraint(
            "production_order_id", "completion_number", name="uq_production_completions_number"
        ),
        CheckConstraint("quantity_completed > 0", name="ck_production_completions_qty"),
        CheckConstraint("quantity_rejected >= 0", name="ck_production_completions_rejected"),
        Index("ix_production_completions_order", "production_order_id"),
        Index("ix_production_completions_posted", "posted_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="RESTRICT")
    )
    completion_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_completed: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_rejected: Mapped[Decimal] = mapped_column(
        Numeric(18, 6), nullable=False, default=0, server_default="0"
    )
    destination_warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_warehouses.id", ondelete="RESTRICT")
    )
    destination_location_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_storage_locations.id", ondelete="RESTRICT")
    )
    inventory_document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_documents.id", ondelete="RESTRICT")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductionOutputSerialModel(Base):
    __tablename__ = "production_output_serials"
    __table_args__ = (
        UniqueConstraint("inventory_serial_id", name="uq_production_output_serial_inventory"),
        UniqueConstraint("serial_number_snapshot", name="uq_production_output_serial_number"),
        Index("ix_production_output_serials_order", "production_order_id"),
        Index("ix_production_output_serials_completion", "completion_id"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    completion_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_completions.id", ondelete="CASCADE")
    )
    inventory_serial_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_serials.id", ondelete="RESTRICT")
    )
    product_item_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    serial_number_snapshot: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProductionOrderCommentModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "production_order_comments"
    __table_args__ = (Index("ix_production_order_comments_order", "production_order_id"),)

    production_order_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("production_orders.id", ondelete="CASCADE")
    )
    author_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
