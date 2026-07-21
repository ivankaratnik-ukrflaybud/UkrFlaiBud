"""Add canonical BOM permissions.

Revision ID: 20260720_0010
Revises: 20260717_0009
Create Date: 2026-07-20 10:00:00.000000

"""

from collections.abc import Iterable, Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260720_0010"
down_revision: str | None = "20260717_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CANONICAL_BOM_PERMISSIONS = {
    "bom.read": ("Специфікації", "Перегляд специфікацій і версій", "bom"),
    "bom.create": (
        "Створення специфікацій",
        "Створення специфікацій і нових версій BOM",
        "bom",
    ),
    "bom.edit": (
        "Редагування специфікацій",
        "Редагування чернеток специфікацій, версій і позицій",
        "bom",
    ),
    "bom.approve": (
        "Затвердження специфікацій",
        "Затвердження та архівування версій специфікацій",
        "bom",
    ),
    "bom.attachments": (
        "Файли специфікацій",
        "Керування кресленнями, фото та іншими файлами специфікацій",
        "bom",
    ),
}

ROLE_PERMISSION_CODES = {
    "bom_designer": [
        "bom.read",
        "bom.create",
        "bom.edit",
        "bom.export",
        "bom.import",
        "bom.attachments",
        "inventory.items.read",
        "inventory.units.read",
    ],
    "bom_technologist": [
        "bom.read",
        "bom.create",
        "bom.edit",
        "bom.export",
        "bom.import",
        "bom.attachments",
        "inventory.items.read",
        "inventory.units.read",
    ],
    "bom_viewer": ["bom.read", "bom.export"],
    "bom_approver": ["bom.read", "bom.approve", "bom.export"],
}


def upgrade() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("module", sa.String()),
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
    for code, (name, description, module) in CANONICAL_BOM_PERMISSIONS.items():
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

    for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
        role_id = connection.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": role_code}
        ).scalar()
        if role_id is not None:
            _insert_role_permissions(
                role_permissions_table,
                role_id,
                [
                    _permission_id(permission_ids, permission_code)
                    for permission_code in permission_codes
                ],
            )

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
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code IN "
            "('bom.read', 'bom.create', 'bom.edit', 'bom.approve', 'bom.attachments'))"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM permissions WHERE code IN "
            "('bom.read', 'bom.create', 'bom.edit', 'bom.approve', 'bom.attachments')"
        )
    )
