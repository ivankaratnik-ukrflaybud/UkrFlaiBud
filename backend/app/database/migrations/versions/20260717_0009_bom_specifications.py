"""BOM specifications.

Revision ID: 20260717_0009
Revises: 20260717_0008
Create Date: 2026-07-17 09:00:00.000000

"""

from collections.abc import Iterable, Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260717_0009"
down_revision: str | None = "20260717_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BOM_PERMISSIONS = {
    "bom.specifications.read": ("Специфікації", "Перегляд специфікацій і версій", "bom"),
    "bom.specifications.create": (
        "Створення специфікацій",
        "Створення нових специфікацій виробів",
        "bom",
    ),
    "bom.specifications.edit": (
        "Редагування специфікацій",
        "Редагування реквізитів специфікацій",
        "bom",
    ),
    "bom.specifications.delete": (
        "Архівування специфікацій",
        "Архівування та деактивація специфікацій",
        "bom",
    ),
    "bom.versions.create": (
        "Створення версій специфікацій",
        "Створення нових версій на основі чинних специфікацій",
        "bom",
    ),
    "bom.versions.edit": (
        "Редагування версій специфікацій",
        "Редагування чернеток версій і позицій",
        "bom",
    ),
    "bom.versions.review": (
        "Перегляд версій специфікацій",
        "Передавання версій специфікацій на перегляд",
        "bom",
    ),
    "bom.versions.approve": (
        "Затвердження специфікацій",
        "Затвердження та заміна версій специфікацій",
        "bom",
    ),
    "bom.export": ("Експорт специфікацій", "Завантаження PDF та Excel", "bom"),
    "bom.import": ("Імпорт специфікацій", "Імпорт позицій із XLSX", "bom"),
    "bom.attachments.manage": (
        "Файли специфікацій",
        "Керування кресленнями, фото та іншими файлами специфікацій",
        "bom",
    ),
    "bom.audit.read": ("Аудит специфікацій", "Перегляд аудиту специфікацій", "bom"),
}

BOM_ROLES = {
    "bom_designer": (
        "Конструктор",
        "Створення та редагування чернеток специфікацій і позицій.",
        [
            "bom.specifications.read",
            "bom.specifications.create",
            "bom.specifications.edit",
            "bom.versions.create",
            "bom.versions.edit",
            "bom.export",
            "bom.import",
            "bom.attachments.manage",
            "inventory.items.read",
            "inventory.units.read",
        ],
    ),
    "bom_technologist": (
        "Технолог",
        "Підготовка, перевірка та імпорт технологічних специфікацій.",
        [
            "bom.specifications.read",
            "bom.specifications.create",
            "bom.specifications.edit",
            "bom.versions.create",
            "bom.versions.edit",
            "bom.versions.review",
            "bom.export",
            "bom.import",
            "bom.attachments.manage",
            "inventory.items.read",
            "inventory.units.read",
        ],
    ),
    "bom_viewer": (
        "Перегляд специфікацій",
        "Перегляд, друк та експорт специфікацій без змін.",
        ["bom.specifications.read", "bom.export"],
    ),
    "bom_approver": (
        "Затвердження специфікацій",
        "Перегляд, погодження і затвердження версій специфікацій.",
        [
            "bom.specifications.read",
            "bom.versions.review",
            "bom.versions.approve",
            "bom.export",
        ],
    ),
}


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
        "bom_specifications",
        *entity_columns(),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "specification_type", sa.String(length=32), server_default="product", nullable=False
        ),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("current_version_number", sa.Integer(), server_default="1", nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("author_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.CheckConstraint(
            "specification_type IN ('product', 'assembly', 'semi_finished', 'kit', "
            "'packaging', 'spare_parts_kit', 'other')",
            name="ck_bom_specifications_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'under_review', 'approved', 'archived')",
            name="ck_bom_specifications_status",
        ),
        sa.CheckConstraint("current_version_number >= 1", name="ck_bom_specifications_version"),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_bom_specifications_organization_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["product_item_id"],
            ["inventory_items.id"],
            name="fk_bom_specifications_product_item_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["author_employee_id"],
            ["employees.id"],
            name="fk_bom_specifications_author_employee_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_employee_id"],
            ["employees.id"],
            name="fk_bom_specifications_approved_by_employee_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_bom_specifications_created_by_user_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bom_specifications"),
        sa.UniqueConstraint("organization_id", "code", name="uq_bom_specifications_org_code"),
    )
    op.create_index(
        "ix_bom_specifications_organization_id", "bom_specifications", ["organization_id"]
    )
    op.create_index(
        "ix_bom_specifications_product_item_id", "bom_specifications", ["product_item_id"]
    )
    op.create_index("ix_bom_specifications_status", "bom_specifications", ["status"])
    op.create_index("ix_bom_specifications_is_active", "bom_specifications", ["is_active"])
    op.create_index("ix_bom_specifications_name", "bom_specifications", ["name"])

    op.create_table(
        "bom_versions",
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("bom_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="draft", nullable=False),
        sa.Column("change_reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("approved_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("snapshot_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.CheckConstraint(
            "status IN ('draft', 'under_review', 'approved', 'superseded', 'archived')",
            name="ck_bom_versions_status",
        ),
        sa.CheckConstraint("version_number >= 1", name="ck_bom_versions_number_positive"),
        sa.ForeignKeyConstraint(
            ["bom_id"],
            ["bom_specifications.id"],
            name="fk_bom_versions_bom_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            name="fk_bom_versions_created_by_user_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by_user_id"],
            ["users.id"],
            name="fk_bom_versions_approved_by_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bom_versions"),
        sa.UniqueConstraint("bom_id", "version_number", name="uq_bom_versions_number"),
    )
    op.create_index("ix_bom_versions_bom_id", "bom_versions", ["bom_id"])
    op.create_index("ix_bom_versions_status", "bom_versions", ["status"])

    op.create_table(
        "bom_lines",
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
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("bom_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("parent_line_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("inventory_item_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("position_code", sa.String(length=96), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit_of_measure_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("waste_percentage", sa.Numeric(5, 2), server_default="0", nullable=False),
        sa.Column("is_optional", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_alternative", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("alternative_group", sa.String(length=80), nullable=True),
        sa.Column("reference_designator", sa.String(length=128), nullable=True),
        sa.Column("drawing_number", sa.String(length=128), nullable=True),
        sa.Column("manufacturer", sa.String(length=255), nullable=True),
        sa.Column("manufacturer_part_number", sa.String(length=128), nullable=True),
        sa.Column("technical_requirements", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=32), server_default="manual", nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_bom_lines_quantity_positive"),
        sa.CheckConstraint(
            "waste_percentage >= 0 AND waste_percentage <= 100",
            name="ck_bom_lines_waste_percentage",
        ),
        sa.CheckConstraint(
            "source_type IN ('inventory_item', 'manual', 'subassembly')",
            name="ck_bom_lines_source_type",
        ),
        sa.CheckConstraint("id <> parent_line_id", name="ck_bom_lines_not_self_parent"),
        sa.ForeignKeyConstraint(
            ["bom_version_id"],
            ["bom_versions.id"],
            name="fk_bom_lines_bom_version_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_line_id"],
            ["bom_lines.id"],
            name="fk_bom_lines_parent_line_id",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["inventory_item_id"],
            ["inventory_items.id"],
            name="fk_bom_lines_inventory_item_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["unit_of_measure_id"],
            ["inventory_units.id"],
            name="fk_bom_lines_unit_of_measure_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bom_lines"),
        sa.UniqueConstraint("bom_version_id", "line_number", name="uq_bom_lines_version_number"),
    )
    op.create_index("ix_bom_lines_version_id", "bom_lines", ["bom_version_id"])
    op.create_index("ix_bom_lines_parent_line_id", "bom_lines", ["parent_line_id"])
    op.create_index("ix_bom_lines_inventory_item_id", "bom_lines", ["inventory_item_id"])
    op.create_index("ix_bom_lines_unit_of_measure_id", "bom_lines", ["unit_of_measure_id"])
    op.create_index("ix_bom_lines_sort_order", "bom_lines", ["sort_order"])

    op.create_table(
        "bom_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("bom_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["bom_version_id"],
            ["bom_versions.id"],
            name="fk_bom_attachments_bom_version_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by_user_id"],
            ["users.id"],
            name="fk_bom_attachments_uploaded_by_user_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_bom_attachments"),
    )
    op.create_index("ix_bom_attachments_version_id", "bom_attachments", ["bom_version_id"])
    op.create_index("ix_bom_attachments_deleted_at", "bom_attachments", ["deleted_at"])
    seed_bom_access()


def seed_bom_access() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("module", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    connection = op.get_bind()
    permission_ids: dict[str, object] = {}
    for code, (name, description, module) in BOM_PERMISSIONS.items():
        existing = connection.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code}
        ).scalar()
        if existing is None:
            permission_id = uuid4()
            op.bulk_insert(
                permissions_table,
                [
                    {
                        "id": permission_id,
                        "code": code,
                        "name": name,
                        "description": description,
                        "module": module,
                        "is_active": True,
                    }
                ],
            )
            permission_ids[code] = permission_id
        else:
            permission_ids[code] = existing
    for code, (name, description, permission_codes) in BOM_ROLES.items():
        role_id = connection.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": code}
        ).scalar()
        if role_id is None:
            role_id = uuid4()
            op.bulk_insert(
                roles_table,
                [
                    {
                        "id": role_id,
                        "name": name,
                        "code": code,
                        "description": description,
                        "is_system": True,
                        "is_active": True,
                    }
                ],
            )
        role_permission_ids = [
            _permission_id(permission_ids, permission_code) for permission_code in permission_codes
        ]
        _insert_role_permissions(role_permissions_table, role_id, role_permission_ids)
    admin_role_id = connection.execute(
        sa.text("SELECT id FROM roles WHERE code = 'system_admin'")
    ).scalar()
    if admin_role_id is not None:
        _insert_role_permissions(role_permissions_table, admin_role_id, permission_ids.values())


def _insert_role_permissions(
    role_permissions_table: sa.TableClause, role_id: object, permission_ids: Iterable[object]
) -> None:
    connection = op.get_bind()
    for permission_id in permission_ids:
        exists = connection.execute(
            sa.text(
                "SELECT 1 FROM role_permissions WHERE role_id = :role_id "
                "AND permission_id = :permission_id"
            ),
            {"role_id": role_id, "permission_id": permission_id},
        ).scalar()
        if exists is None:
            op.bulk_insert(
                role_permissions_table,
                [{"id": uuid4(), "role_id": role_id, "permission_id": permission_id}],
            )


def _permission_id(permission_ids: dict[str, object], code: str) -> object:
    if code in permission_ids:
        return permission_ids[code]
    existing = (
        op.get_bind()
        .execute(sa.text("SELECT id FROM permissions WHERE code = :code"), {"code": code})
        .scalar()
    )
    if existing is None:
        raise RuntimeError(f"Permission {code} is required for BOM role seeding.")
    return existing


def downgrade() -> None:
    op.drop_index("ix_bom_attachments_deleted_at", table_name="bom_attachments")
    op.drop_index("ix_bom_attachments_version_id", table_name="bom_attachments")
    op.drop_table("bom_attachments")
    op.drop_index("ix_bom_lines_sort_order", table_name="bom_lines")
    op.drop_index("ix_bom_lines_unit_of_measure_id", table_name="bom_lines")
    op.drop_index("ix_bom_lines_inventory_item_id", table_name="bom_lines")
    op.drop_index("ix_bom_lines_parent_line_id", table_name="bom_lines")
    op.drop_index("ix_bom_lines_version_id", table_name="bom_lines")
    op.drop_table("bom_lines")
    op.drop_index("ix_bom_versions_status", table_name="bom_versions")
    op.drop_index("ix_bom_versions_bom_id", table_name="bom_versions")
    op.drop_table("bom_versions")
    op.drop_index("ix_bom_specifications_name", table_name="bom_specifications")
    op.drop_index("ix_bom_specifications_is_active", table_name="bom_specifications")
    op.drop_index("ix_bom_specifications_status", table_name="bom_specifications")
    op.drop_index("ix_bom_specifications_product_item_id", table_name="bom_specifications")
    op.drop_index("ix_bom_specifications_organization_id", table_name="bom_specifications")
    op.drop_table("bom_specifications")
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code LIKE 'bom.%')"
        )
    )
    op.execute(sa.text("DELETE FROM roles WHERE code LIKE 'bom_%'"))
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'bom.%'"))
