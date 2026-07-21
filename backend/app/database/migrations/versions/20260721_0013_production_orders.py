"""Add production orders module.

Revision ID: 20260721_0013
Revises: 20260721_0012
Create Date: 2026-07-21 15:00:00.000000

"""

# ruff: noqa: E501
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260721_0013"
down_revision: str | None = "20260721_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRODUCTION_PERMISSIONS = {
    "production.read": ("Виробництво", "Перегляд виробничих замовлень", "production"),
    "production.create": ("Створення замовлень", "Створення виробничих замовлень", "production"),
    "production.edit": (
        "Редагування замовлень",
        "Планування, випуск і зміна виробничих замовлень",
        "production",
    ),
    "production.reserve": (
        "Резервування матеріалів",
        "Резервування та зняття резерву матеріалів",
        "production",
    ),
    "production.issue": (
        "Видача матеріалів",
        "Видача і повернення матеріалів виробництва",
        "production",
    ),
    "production.consume": (
        "Списання матеріалів",
        "Фіксація використання і браку матеріалів",
        "production",
    ),
    "production.stages": (
        "Етапи виробництва",
        "Керування етапами виробничих замовлень",
        "production",
    ),
    "production.complete": ("Готова продукція", "Оприбуткування готової продукції", "production"),
    "production.export": ("Експорт виробництва", "PDF та Excel виробничих замовлень", "production"),
    "production.settings": ("Налаштування виробництва", "Керування шаблонами етапів", "production"),
}


def upgrade() -> None:
    uuid = postgresql.UUID(as_uuid=True)
    now = sa.text("now()")
    op.create_table(
        "production_orders",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("order_number", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("product_item_id", uuid, sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("bom_id", uuid, sa.ForeignKey("bom_specifications.id"), nullable=False),
        sa.Column("bom_version_id", uuid, sa.ForeignKey("bom_versions.id"), nullable=False),
        sa.Column("bom_version_number", sa.Integer(), nullable=False),
        sa.Column("order_type", sa.String(32), nullable=False, server_default="standard"),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("priority", sa.String(32), nullable=False, server_default="normal"),
        sa.Column("site_id", uuid, sa.ForeignKey("inventory_sites.id"), nullable=False),
        sa.Column("department_id", uuid, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column(
            "production_warehouse_id", uuid, sa.ForeignKey("inventory_warehouses.id"), nullable=True
        ),
        sa.Column(
            "material_warehouse_id", uuid, sa.ForeignKey("inventory_warehouses.id"), nullable=False
        ),
        sa.Column(
            "finished_goods_warehouse_id",
            uuid,
            sa.ForeignKey("inventory_warehouses.id"),
            nullable=False,
        ),
        sa.Column("planned_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("completed_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("rejected_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("unit_of_measure_id", uuid, sa.ForeignKey("inventory_units.id"), nullable=False),
        sa.Column("planned_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("responsible_employee_id", uuid, sa.ForeignKey("employees.id"), nullable=True),
        sa.Column(
            "production_manager_employee_id", uuid, sa.ForeignKey("employees.id"), nullable=True
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("suspension_reason", sa.Text(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("created_by", uuid, nullable=True),
        sa.Column("updated_by", uuid, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", uuid, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("organization_id", "order_number", name="uq_production_orders_number"),
        sa.CheckConstraint("planned_quantity > 0", name="ck_production_orders_planned_qty"),
        sa.CheckConstraint("completed_quantity >= 0", name="ck_production_orders_completed_qty"),
        sa.CheckConstraint("rejected_quantity >= 0", name="ck_production_orders_rejected_qty"),
    )
    for index_name, columns in {
        "ix_production_orders_organization_id": ["organization_id"],
        "ix_production_orders_number": ["order_number"],
        "ix_production_orders_status": ["status"],
        "ix_production_orders_site_id": ["site_id"],
        "ix_production_orders_product_item_id": ["product_item_id"],
        "ix_production_orders_planned_start": ["planned_start_date"],
        "ix_production_orders_planned_end": ["planned_end_date"],
        "ix_production_orders_responsible": ["responsible_employee_id"],
        "ix_production_orders_active": ["is_active"],
    }.items():
        op.create_index(index_name, "production_orders", columns)

    op.create_table(
        "production_order_bom_snapshots",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column("source_bom_id", uuid, sa.ForeignKey("bom_specifications.id"), nullable=False),
        sa.Column("source_bom_version_id", uuid, sa.ForeignKey("bom_versions.id"), nullable=False),
        sa.Column("source_bom_version_number", sa.Integer(), nullable=False),
        sa.Column("specification_code", sa.String(96), nullable=False),
        sa.Column("specification_name", sa.String(255), nullable=False),
        sa.Column("product_code", sa.String(96), nullable=True),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("unit_name", sa.String(255), nullable=False),
        sa.Column("unit_symbol", sa.String(32), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("snapshot_json", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
    )
    op.create_index(
        "ix_production_snapshots_order_id",
        "production_order_bom_snapshots",
        ["production_order_id"],
    )

    op.create_table(
        "production_material_requirements",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column("source_bom_line_id", uuid, sa.ForeignKey("bom_lines.id"), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column(
            "parent_requirement_id",
            uuid,
            sa.ForeignKey("production_material_requirements.id"),
            nullable=True,
        ),
        sa.Column("inventory_item_id", uuid, sa.ForeignKey("inventory_items.id"), nullable=True),
        sa.Column("item_code_snapshot", sa.String(96), nullable=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("required_quantity_per_unit", sa.Numeric(18, 6), nullable=False),
        sa.Column("waste_percentage", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("planned_quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("reserved_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("issued_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("returned_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("consumed_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("scrapped_quantity", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column("unit_of_measure_id", uuid, sa.ForeignKey("inventory_units.id"), nullable=False),
        sa.Column("unit_name_snapshot", sa.String(255), nullable=False),
        sa.Column("unit_symbol_snapshot", sa.String(32), nullable=False),
        sa.Column("is_optional", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_alternative", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("alternative_group", sa.String(80), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("technical_requirements", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint(
            "production_order_id", "line_number", name="uq_production_requirements_line"
        ),
        sa.CheckConstraint("required_quantity_per_unit > 0", name="ck_prod_req_per_unit_positive"),
        sa.CheckConstraint("planned_quantity >= 0", name="ck_prod_req_planned_nonnegative"),
    )
    op.create_index(
        "ix_production_requirements_order_id",
        "production_material_requirements",
        ["production_order_id"],
    )
    op.create_index(
        "ix_production_requirements_item_id",
        "production_material_requirements",
        ["inventory_item_id"],
    )

    op.create_table(
        "production_material_reservations",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column(
            "material_requirement_id",
            uuid,
            sa.ForeignKey("production_material_requirements.id"),
            nullable=False,
        ),
        sa.Column("inventory_item_id", uuid, sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("warehouse_id", uuid, sa.ForeignKey("inventory_warehouses.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("quantity > 0", name="ck_production_reservations_quantity"),
    )
    op.create_index(
        "ix_production_reservations_order_id",
        "production_material_reservations",
        ["production_order_id"],
    )
    op.create_index(
        "ix_production_reservations_requirement_id",
        "production_material_reservations",
        ["material_requirement_id"],
    )
    op.create_index(
        "ix_production_reservations_item_warehouse",
        "production_material_reservations",
        ["inventory_item_id", "warehouse_id"],
    )
    op.create_index(
        "ix_production_reservations_status", "production_material_reservations", ["status"]
    )

    op.create_table(
        "production_stage_templates",
        sa.Column("id", uuid, primary_key=True),
        sa.Column("organization_id", uuid, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("default_sequence", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("default_department_id", uuid, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("created_by", uuid, nullable=True),
        sa.Column("updated_by", uuid, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", uuid, nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("organization_id", "code", name="uq_production_stage_templates_code"),
    )
    op.create_index(
        "ix_production_stage_templates_org", "production_stage_templates", ["organization_id"]
    )
    op.create_index(
        "ix_production_stage_templates_active", "production_stage_templates", ["is_active"]
    )

    op.create_table(
        "production_order_stages",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column(
            "stage_template_id", uuid, sa.ForeignKey("production_stage_templates.id"), nullable=True
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("code_snapshot", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("department_id", uuid, sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("workplace_id", uuid, nullable=True),
        sa.Column("responsible_employee_id", uuid, sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column("completion_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint(
            "production_order_id", "sequence", name="uq_production_order_stage_seq"
        ),
        sa.CheckConstraint(
            "progress_percent >= 0 AND progress_percent <= 100", name="ck_production_stage_progress"
        ),
    )
    op.create_index(
        "ix_production_order_stages_order", "production_order_stages", ["production_order_id"]
    )
    op.create_index("ix_production_order_stages_status", "production_order_stages", ["status"])

    op.create_table(
        "production_material_transactions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column(
            "inventory_document_id", uuid, sa.ForeignKey("inventory_documents.id"), nullable=True
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="posted"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("posted_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_production_material_transactions_order",
        "production_material_transactions",
        ["production_order_id"],
    )
    op.create_index(
        "ix_production_material_transactions_created",
        "production_material_transactions",
        ["created_at"],
    )

    op.create_table(
        "production_material_transaction_lines",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "transaction_id",
            uuid,
            sa.ForeignKey("production_material_transactions.id"),
            nullable=False,
        ),
        sa.Column(
            "material_requirement_id",
            uuid,
            sa.ForeignKey("production_material_requirements.id"),
            nullable=False,
        ),
        sa.Column("inventory_item_id", uuid, sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("warehouse_id", uuid, sa.ForeignKey("inventory_warehouses.id"), nullable=False),
        sa.Column(
            "location_id", uuid, sa.ForeignKey("inventory_storage_locations.id"), nullable=True
        ),
        sa.Column("lot_id", uuid, sa.ForeignKey("inventory_lots.id"), nullable=True),
        sa.Column("serial_id", uuid, sa.ForeignKey("inventory_serials.id"), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("quantity > 0", name="ck_production_material_tx_lines_quantity"),
    )
    op.create_index(
        "ix_production_material_tx_lines_transaction",
        "production_material_transaction_lines",
        ["transaction_id"],
    )
    op.create_index(
        "ix_production_material_tx_lines_requirement",
        "production_material_transaction_lines",
        ["material_requirement_id"],
    )

    op.create_table(
        "production_completions",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column("completion_number", sa.Integer(), nullable=False),
        sa.Column("quantity_completed", sa.Numeric(18, 6), nullable=False),
        sa.Column("quantity_rejected", sa.Numeric(18, 6), nullable=False, server_default="0"),
        sa.Column(
            "destination_warehouse_id",
            uuid,
            sa.ForeignKey("inventory_warehouses.id"),
            nullable=False,
        ),
        sa.Column(
            "destination_location_id",
            uuid,
            sa.ForeignKey("inventory_storage_locations.id"),
            nullable=True,
        ),
        sa.Column(
            "inventory_document_id", uuid, sa.ForeignKey("inventory_documents.id"), nullable=False
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("completed_by_employee_id", uuid, sa.ForeignKey("employees.id"), nullable=True),
        sa.Column("created_by_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.UniqueConstraint(
            "production_order_id", "completion_number", name="uq_production_completions_number"
        ),
        sa.CheckConstraint("quantity_completed > 0", name="ck_production_completions_qty"),
        sa.CheckConstraint("quantity_rejected >= 0", name="ck_production_completions_rejected"),
    )
    op.create_index(
        "ix_production_completions_order", "production_completions", ["production_order_id"]
    )
    op.create_index("ix_production_completions_posted", "production_completions", ["posted_at"])

    op.create_table(
        "production_output_serials",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column(
            "completion_id", uuid, sa.ForeignKey("production_completions.id"), nullable=False
        ),
        sa.Column(
            "inventory_serial_id", uuid, sa.ForeignKey("inventory_serials.id"), nullable=False
        ),
        sa.Column("product_item_id", uuid, sa.ForeignKey("inventory_items.id"), nullable=False),
        sa.Column("serial_number_snapshot", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.UniqueConstraint("inventory_serial_id", name="uq_production_output_serial_inventory"),
        sa.UniqueConstraint("serial_number_snapshot", name="uq_production_output_serial_number"),
    )
    op.create_index(
        "ix_production_output_serials_order", "production_output_serials", ["production_order_id"]
    )
    op.create_index(
        "ix_production_output_serials_completion", "production_output_serials", ["completion_id"]
    )

    op.create_table(
        "production_order_comments",
        sa.Column("id", uuid, primary_key=True),
        sa.Column(
            "production_order_id", uuid, sa.ForeignKey("production_orders.id"), nullable=False
        ),
        sa.Column("author_user_id", uuid, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_production_order_comments_order", "production_order_comments", ["production_order_id"]
    )
    _seed_access()


def downgrade() -> None:
    for table in [
        "production_order_comments",
        "production_output_serials",
        "production_completions",
        "production_material_transaction_lines",
        "production_material_transactions",
        "production_order_stages",
        "production_stage_templates",
        "production_material_reservations",
        "production_material_requirements",
        "production_order_bom_snapshots",
        "production_orders",
    ]:
        op.drop_table(table)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code LIKE 'production.%')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'production.%'"))


def _seed_access() -> None:
    for code, (name, description, module) in PRODUCTION_PERMISSIONS.items():
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, name, description, module, is_active) "
                "VALUES (gen_random_uuid(), :code, :name, :description, :module, true) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, "
                "description = EXCLUDED.description, module = EXCLUDED.module, is_active = true"
            ).bindparams(code=code, name=name, description=description, module=module)
        )
    op.execute(
        sa.text(
            "INSERT INTO roles (id, name, code, description, is_system, is_active, "
            "created_at, updated_at, version) "
            "VALUES (gen_random_uuid(), 'Керівник виробництва', 'production_manager', "
            "'Повний операційний доступ до виробничих замовлень.', true, true, now(), now(), 1) "
            "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, description = EXCLUDED.description, is_active = true"
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO role_permissions (id, role_id, permission_id) "
            "SELECT gen_random_uuid(), r.id, p.id FROM roles r CROSS JOIN permissions p "
            "WHERE r.code = 'production_manager' AND p.code LIKE 'production.%' "
            "ON CONFLICT (role_id, permission_id) DO NOTHING"
        )
    )
