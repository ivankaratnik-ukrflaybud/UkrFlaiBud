from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import EntityMixin
from app.modules.organizations.domain.entities import EmployeeStatus


class OrganizationModel(EntityMixin, Base):
    __tablename__ = "organizations"
    __table_args__ = (
        UniqueConstraint("edrpou", name="uq_organizations_edrpou"),
        Index("ix_organizations_name", "name"),
        Index("ix_organizations_is_active", "is_active"),
        CheckConstraint("char_length(edrpou) BETWEEN 8 AND 12", name="ck_organizations_edrpou_len"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str] = mapped_column(String(120), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    edrpou: Mapped[str] = mapped_column(String(12), nullable=False)
    tax_number: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class DepartmentModel(EntityMixin, Base):
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_departments_organization_code"),
        Index("ix_departments_organization_id", "organization_id"),
        Index("ix_departments_parent_department_id", "parent_department_id"),
        Index("ix_departments_name", "name"),
        Index("ix_departments_is_active", "is_active"),
        CheckConstraint("id <> parent_department_id", name="ck_departments_not_self_parent"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_employee_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class PositionModel(EntityMixin, Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("organization_id", "code", name="uq_positions_organization_code"),
        Index("ix_positions_organization_id", "organization_id"),
        Index("ix_positions_department_id", "department_id"),
        Index("ix_positions_name", "name"),
        Index("ix_positions_is_active", "is_active"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )


class EmployeeModel(EntityMixin, Base):
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "personnel_number", name="uq_employees_organization_personnel"
        ),
        Index("ix_employees_organization_id", "organization_id"),
        Index("ix_employees_department_id", "department_id"),
        Index("ix_employees_position_id", "position_id"),
        Index("ix_employees_supervisor_employee_id", "supervisor_employee_id"),
        Index("ix_employees_status", "status"),
        Index("ix_employees_name", "last_name", "first_name", "middle_name"),
        CheckConstraint("id <> supervisor_employee_id", name="ck_employees_not_self_supervisor"),
        CheckConstraint(
            "status IN ('active', 'on_leave', 'terminated')",
            name="ck_employees_status",
        ),
        CheckConstraint(
            "termination_date IS NULL OR hire_date IS NULL OR termination_date >= hire_date",
            name="ck_employees_dates",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    department_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
    )
    position_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("positions.id", ondelete="SET NULL"),
        nullable=True,
    )
    personnel_number: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    last_name: Mapped[str] = mapped_column(String(120), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    hire_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=EmployeeStatus.ACTIVE.value,
        server_default=EmployeeStatus.ACTIVE.value,
    )
    supervisor_employee_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
