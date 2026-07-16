"""Organization core business module.

Revision ID: 20260716_0002
Revises: 20260716_0001
Create Date: 2026-07-16 00:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0002"
down_revision: str | None = "20260716_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def entity_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        *entity_columns(),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("short_name", sa.String(length=120), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("edrpou", sa.String(length=12), nullable=False),
        sa.Column("tax_number", sa.String(length=32), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint(
            "char_length(edrpou) BETWEEN 8 AND 12", name="ck_organizations_edrpou_len"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("edrpou", name="uq_organizations_edrpou"),
    )
    op.create_index("ix_organizations_is_active", "organizations", ["is_active"])
    op.create_index("ix_organizations_name", "organizations", ["name"])

    op.create_table(
        "departments",
        *entity_columns(),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("parent_department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manager_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.CheckConstraint("id <> parent_department_id", name="ck_departments_not_self_parent"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_departments_organization_id"
        ),
        sa.ForeignKeyConstraint(
            ["parent_department_id"],
            ["departments.id"],
            name="fk_departments_parent_department_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_departments"),
        sa.UniqueConstraint("organization_id", "code", name="uq_departments_organization_code"),
    )
    op.create_index("ix_departments_is_active", "departments", ["is_active"])
    op.create_index("ix_departments_name", "departments", ["name"])
    op.create_index("ix_departments_organization_id", "departments", ["organization_id"])
    op.create_index("ix_departments_parent_department_id", "departments", ["parent_department_id"])

    op.create_table(
        "positions",
        *entity_columns(),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_positions_department_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_positions_organization_id"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_positions"),
        sa.UniqueConstraint("organization_id", "code", name="uq_positions_organization_code"),
    )
    op.create_index("ix_positions_department_id", "positions", ["department_id"])
    op.create_index("ix_positions_is_active", "positions", ["is_active"])
    op.create_index("ix_positions_name", "positions", ["name"])
    op.create_index("ix_positions_organization_id", "positions", ["organization_id"])

    op.create_table(
        "employees",
        *entity_columns(),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("personnel_number", sa.String(length=64), nullable=True),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("middle_name", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("hire_date", sa.Date(), nullable=True),
        sa.Column("termination_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("supervisor_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint("id <> supervisor_employee_id", name="ck_employees_not_self_supervisor"),
        sa.CheckConstraint(
            "status IN ('active', 'on_leave', 'terminated')", name="ck_employees_status"
        ),
        sa.CheckConstraint(
            "termination_date IS NULL OR hire_date IS NULL OR termination_date >= hire_date",
            name="ck_employees_dates",
        ),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_employees_department_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"], name="fk_employees_organization_id"
        ),
        sa.ForeignKeyConstraint(
            ["position_id"], ["positions.id"], name="fk_employees_position_id", ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["supervisor_employee_id"],
            ["employees.id"],
            name="fk_employees_supervisor_employee_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_employees"),
        sa.UniqueConstraint(
            "organization_id", "personnel_number", name="uq_employees_organization_personnel"
        ),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index("ix_employees_name", "employees", ["last_name", "first_name", "middle_name"])
    op.create_index("ix_employees_organization_id", "employees", ["organization_id"])
    op.create_index("ix_employees_position_id", "employees", ["position_id"])
    op.create_index("ix_employees_status", "employees", ["status"])
    op.create_index("ix_employees_supervisor_employee_id", "employees", ["supervisor_employee_id"])


def downgrade() -> None:
    op.drop_index("ix_employees_supervisor_employee_id", table_name="employees")
    op.drop_index("ix_employees_status", table_name="employees")
    op.drop_index("ix_employees_position_id", table_name="employees")
    op.drop_index("ix_employees_organization_id", table_name="employees")
    op.drop_index("ix_employees_name", table_name="employees")
    op.drop_index("ix_employees_department_id", table_name="employees")
    op.drop_table("employees")

    op.drop_index("ix_positions_organization_id", table_name="positions")
    op.drop_index("ix_positions_name", table_name="positions")
    op.drop_index("ix_positions_is_active", table_name="positions")
    op.drop_index("ix_positions_department_id", table_name="positions")
    op.drop_table("positions")

    op.drop_index("ix_departments_parent_department_id", table_name="departments")
    op.drop_index("ix_departments_organization_id", table_name="departments")
    op.drop_index("ix_departments_name", table_name="departments")
    op.drop_index("ix_departments_is_active", table_name="departments")
    op.drop_table("departments")

    op.drop_index("ix_organizations_name", table_name="organizations")
    op.drop_index("ix_organizations_is_active", table_name="organizations")
    op.drop_table("organizations")
