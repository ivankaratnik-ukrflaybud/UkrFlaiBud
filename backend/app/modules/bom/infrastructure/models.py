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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import EntityMixin, IdMixin, TimestampMixin, VersionMixin
from app.modules.bom.domain.entities import (
    BomLineSourceType,
    BomVersionStatus,
    SpecificationStatus,
    SpecificationType,
)


class BomSpecificationModel(EntityMixin, Base):
    __tablename__ = "bom_specifications"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_bom_specifications_org_code"),
        CheckConstraint(
            "specification_type IN ('product', 'assembly', 'semi_finished', 'kit', "
            "'packaging', 'spare_parts_kit', 'other')",
            name="ck_bom_specifications_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'under_review', 'approved', 'archived')",
            name="ck_bom_specifications_status",
        ),
        CheckConstraint("current_version_number >= 1", name="ck_bom_specifications_version"),
        Index("ix_bom_specifications_organization_id", "organization_id"),
        Index("ix_bom_specifications_product_item_id", "product_item_id"),
        Index("ix_bom_specifications_status", "status"),
        Index("ix_bom_specifications_is_active", "is_active"),
        Index("ix_bom_specifications_name", "name"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT")
    )
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    product_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    specification_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SpecificationType.PRODUCT.value,
        server_default=SpecificationType.PRODUCT.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=SpecificationStatus.DRAFT.value,
        server_default=SpecificationStatus.DRAFT.value,
    )
    current_version_number: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    author_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    approved_by_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )


class BomVersionModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "bom_versions"
    __table_args__ = (
        UniqueConstraint("bom_id", "version_number", name="uq_bom_versions_number"),
        CheckConstraint(
            "status IN ('draft', 'under_review', 'approved', 'superseded', 'archived')",
            name="ck_bom_versions_status",
        ),
        CheckConstraint("version_number >= 1", name="ck_bom_versions_number_positive"),
        Index("ix_bom_versions_bom_id", "bom_id"),
        Index("ix_bom_versions_status", "status"),
    )

    bom_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_specifications.id", ondelete="RESTRICT")
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    version_label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=BomVersionStatus.DRAFT.value,
        server_default=BomVersionStatus.DRAFT.value,
    )
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    approved_by_user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    effective_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    snapshot_data: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)


class BomLineModel(IdMixin, TimestampMixin, VersionMixin, Base):
    __tablename__ = "bom_lines"
    __table_args__ = (
        UniqueConstraint("bom_version_id", "line_number", name="uq_bom_lines_version_number"),
        CheckConstraint("quantity > 0", name="ck_bom_lines_quantity_positive"),
        CheckConstraint(
            "waste_percentage >= 0 AND waste_percentage <= 100",
            name="ck_bom_lines_waste_percentage",
        ),
        CheckConstraint(
            "source_type IN ('inventory_item', 'manual', 'subassembly')",
            name="ck_bom_lines_source_type",
        ),
        CheckConstraint("id <> parent_line_id", name="ck_bom_lines_not_self_parent"),
        Index("ix_bom_lines_version_id", "bom_version_id"),
        Index("ix_bom_lines_parent_line_id", "parent_line_id"),
        Index("ix_bom_lines_inventory_item_id", "inventory_item_id"),
        Index("ix_bom_lines_unit_of_measure_id", "unit_of_measure_id"),
        Index("ix_bom_lines_sort_order", "sort_order"),
    )

    bom_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_versions.id", ondelete="CASCADE")
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_line_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_lines.id", ondelete="SET NULL")
    )
    inventory_item_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_items.id", ondelete="RESTRICT")
    )
    position_code: Mapped[str | None] = mapped_column(String(96), nullable=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_of_measure_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("inventory_units.id", ondelete="RESTRICT")
    )
    waste_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, default=0, server_default="0"
    )
    is_optional: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    is_alternative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    alternative_group: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reference_designator: Mapped[str | None] = mapped_column(String(128), nullable=True)
    drawing_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    manufacturer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturer_part_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    technical_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=BomLineSourceType.MANUAL.value,
        server_default=BomLineSourceType.MANUAL.value,
    )


class BomAttachmentModel(Base):
    __tablename__ = "bom_attachments"
    __table_args__ = (
        Index("ix_bom_attachments_version_id", "bom_version_id"),
        Index("ix_bom_attachments_deleted_at", "deleted_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    bom_version_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("bom_versions.id", ondelete="CASCADE")
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_by_user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
