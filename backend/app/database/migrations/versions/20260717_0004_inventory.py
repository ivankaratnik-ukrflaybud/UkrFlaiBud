"""Warehouse and item catalog inventory module.

Revision ID: 20260717_0004
Revises: 20260716_0003
Create Date: 2026-07-17 09:00:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

from app.database.base import Base
from app.modules.identity.infrastructure import models as identity_models  # noqa: F401
from app.modules.inventory.infrastructure import models as inventory_models  # noqa: F401
from app.modules.organizations.infrastructure import models as organization_models  # noqa: F401

revision: str = "20260717_0004"
down_revision: str | None = "20260716_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INVENTORY_TABLES = [
    "inventory_sites",
    "inventory_warehouses",
    "inventory_storage_locations",
    "inventory_units",
    "inventory_item_categories",
    "inventory_items",
    "inventory_lots",
    "inventory_serials",
    "inventory_documents",
    "inventory_document_lines",
    "inventory_document_line_serials",
    "inventory_movements",
    "inventory_stock_balances",
    "user_site_access",
    "user_warehouse_access",
]

INVENTORY_PERMISSIONS = {
    "inventory.sites.read": ("Майданчики", "Перегляд майданчиків", "inventory"),
    "inventory.sites.manage": (
        "Керування майданчиками",
        "Створення та редагування майданчиків",
        "inventory",
    ),
    "inventory.warehouses.read": ("Склади", "Перегляд складів", "inventory"),
    "inventory.warehouses.manage": (
        "Керування складами",
        "Створення та редагування складів",
        "inventory",
    ),
    "inventory.locations.read": (
        "Місця зберігання",
        "Перегляд місць зберігання",
        "inventory",
    ),
    "inventory.locations.manage": (
        "Керування місцями зберігання",
        "Створення та редагування місць зберігання",
        "inventory",
    ),
    "inventory.units.read": ("Одиниці виміру", "Перегляд одиниць виміру", "inventory"),
    "inventory.units.manage": (
        "Керування одиницями виміру",
        "Створення та редагування одиниць виміру",
        "inventory",
    ),
    "inventory.categories.read": (
        "Категорії номенклатури",
        "Перегляд категорій номенклатури",
        "inventory",
    ),
    "inventory.categories.manage": (
        "Керування категоріями",
        "Створення та редагування категорій номенклатури",
        "inventory",
    ),
    "inventory.items.read": ("Номенклатура", "Перегляд номенклатури", "inventory"),
    "inventory.items.manage": (
        "Керування номенклатурою",
        "Створення та редагування номенклатури",
        "inventory",
    ),
    "inventory.tracking.read": (
        "Партії та серійні номери",
        "Перегляд партій і серійних номерів",
        "inventory",
    ),
    "inventory.tracking.manage": (
        "Керування відстеженням",
        "Створення партій та серійних номерів",
        "inventory",
    ),
    "inventory.documents.read": (
        "Складські документи",
        "Перегляд складських документів",
        "inventory",
    ),
    "inventory.documents.create": (
        "Створення складських документів",
        "Створення чернеток складських документів",
        "inventory",
    ),
    "inventory.documents.edit": (
        "Редагування складських документів",
        "Редагування чернеток складських документів",
        "inventory",
    ),
    "inventory.documents.post": (
        "Проведення складських документів",
        "Проведення складських документів",
        "inventory",
    ),
    "inventory.documents.cancel": (
        "Скасування складських документів",
        "Скасування та сторнування складських документів",
        "inventory",
    ),
    "inventory.stock.read": ("Залишки", "Перегляд складських залишків", "inventory"),
    "inventory.stock.adjust": (
        "Коригування залишків",
        "Створення складських коригувань",
        "inventory",
    ),
    "inventory.audit.read": ("Аудит складу", "Перегляд складського аудиту", "inventory"),
}

WAREHOUSE_ROLES = {
    "warehouse_clerk": (
        "Комірник",
        "Операційна робота зі складськими документами та залишками.",
        [
            "inventory.sites.read",
            "inventory.warehouses.read",
            "inventory.locations.read",
            "inventory.units.read",
            "inventory.categories.read",
            "inventory.items.read",
            "inventory.tracking.read",
            "inventory.documents.read",
            "inventory.documents.create",
            "inventory.documents.edit",
            "inventory.documents.post",
            "inventory.stock.read",
        ],
    ),
    "warehouse_manager": (
        "Керівник складу",
        "Керування складськими довідниками, документами та доступом.",
        [code for code in INVENTORY_PERMISSIONS if code != "inventory.audit.read"],
    ),
    "warehouse_viewer": (
        "Перегляд складу",
        "Перегляд складських довідників, документів і залишків без змін.",
        [
            "inventory.sites.read",
            "inventory.warehouses.read",
            "inventory.locations.read",
            "inventory.units.read",
            "inventory.categories.read",
            "inventory.items.read",
            "inventory.tracking.read",
            "inventory.documents.read",
            "inventory.stock.read",
        ],
    ),
}

COMMON_UNITS = [
    ("PCS", "штука", "шт", 0),
    ("SET", "комплект", "компл.", 0),
    ("M", "метр", "м", 3),
    ("M2", "квадратний метр", "м²", 3),
    ("KG", "кілограм", "кг", 3),
    ("G", "грам", "г", 3),
    ("L", "літр", "л", 3),
    ("PACK", "упаковка", "уп.", 0),
]


def upgrade() -> None:
    bind = op.get_bind()
    for table in Base.metadata.sorted_tables:
        if table.name in INVENTORY_TABLES:
            table.create(bind)
    seed_permissions(bind)
    seed_initial_inventory_data(bind)


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code LIKE 'inventory.%')"
        )
    )
    bind.execute(sa.text("DELETE FROM roles WHERE code LIKE 'warehouse_%' AND is_system = true"))
    bind.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'inventory.%'"))
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in INVENTORY_TABLES:
            table.drop(bind)


def seed_permissions(bind: sa.Connection) -> None:
    permission_ids: dict[str, str] = {}
    for code, (name, description, module) in INVENTORY_PERMISSIONS.items():
        permission_id = str(uuid4())
        bind.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, name, description, module, is_active)
                VALUES (:id, :code, :name, :description, :module, true)
                ON CONFLICT (code) DO NOTHING
                """
            ),
            {
                "id": permission_id,
                "code": code,
                "name": name,
                "description": description,
                "module": module,
            },
        )
        existing = bind.execute(
            sa.text("SELECT id FROM permissions WHERE code = :code"),
            {"code": code},
        ).scalar_one()
        permission_ids[code] = str(existing)

    system_admin_id = bind.execute(
        sa.text("SELECT id FROM roles WHERE code = 'system_admin'")
    ).scalar_one_or_none()
    if system_admin_id:
        for permission_id in permission_ids.values():
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (id, role_id, permission_id)
                    VALUES (:id, :role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid4()),
                    "role_id": str(system_admin_id),
                    "permission_id": permission_id,
                },
            )

    for code, (name, description, permission_codes) in WAREHOUSE_ROLES.items():
        role_id = bind.execute(
            sa.text("SELECT id FROM roles WHERE code = :code"), {"code": code}
        ).scalar_one_or_none()
        if role_id is None:
            role_id = str(uuid4())
            bind.execute(
                sa.text(
                    """
                    INSERT INTO roles
                        (
                            id, created_at, updated_at, version, name, code, description,
                            is_system, is_active
                        )
                    VALUES (:id, now(), now(), 1, :name, :code, :description, true, true)
                    """
                ),
                {"id": role_id, "name": name, "code": code, "description": description},
            )
        for permission_code in permission_codes:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (id, role_id, permission_id)
                    VALUES (:id, :role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """
                ),
                {
                    "id": str(uuid4()),
                    "role_id": str(role_id),
                    "permission_id": permission_ids[permission_code],
                },
            )


def seed_initial_inventory_data(bind: sa.Connection) -> None:
    seed_organization_id = bind.execute(
        sa.text(
            """
            SELECT id
            FROM organizations
            WHERE is_active = true
            ORDER BY created_at ASC, id ASC
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if seed_organization_id is not None:
        kyiv_id = ensure_site(bind, seed_organization_id, "KYIV", "Київ")
        talne_id = ensure_site(bind, seed_organization_id, "TALNE", "Тальне")
        if kyiv_id is not None:
            ensure_warehouse(bind, seed_organization_id, kyiv_id, "KYIV-MAIN", "Склад Київ")
        if talne_id is not None:
            ensure_warehouse(bind, seed_organization_id, talne_id, "TALNE-MAIN", "Склад Тальне")

        for code, name, symbol, precision in COMMON_UNITS:
            ensure_unit(bind, seed_organization_id, code, name, symbol, precision)


def ensure_site(
    bind: sa.Connection, organization_id: object, code: str, name: str
) -> object | None:
    row = bind.execute(
        sa.text(
            """
            SELECT id, deleted_at
            FROM inventory_sites
            WHERE code = :code
            ORDER BY deleted_at IS NULL DESC, created_at ASC, id ASC
            LIMIT 1
            """
        ),
        {"code": code},
    ).one_or_none()
    if row is not None:
        if row.deleted_at is not None:
            return None
        site_id: object = row.id
        return site_id
    site_id = str(uuid4())
    bind.execute(
        sa.text(
            """
            INSERT INTO inventory_sites
                (id, created_at, updated_at, version, organization_id, code, name, is_active)
            VALUES (:id, now(), now(), 1, :organization_id, :code, :name, true)
            """
        ),
        {"id": site_id, "organization_id": str(organization_id), "code": code, "name": name},
    )
    return site_id


def ensure_warehouse(
    bind: sa.Connection, organization_id: object, site_id: object, code: str, name: str
) -> None:
    existing = bind.execute(
        sa.text(
            """
            SELECT id
            FROM inventory_warehouses
            WHERE code = :code
            ORDER BY deleted_at IS NULL DESC, created_at ASC, id ASC
            LIMIT 1
            """
        ),
        {"code": code},
    ).scalar_one_or_none()
    if existing is not None:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO inventory_warehouses
                (
                    id, created_at, updated_at, version, organization_id, site_id, code, name,
                    warehouse_type, allow_negative_stock, is_active
                )
            VALUES (
                :id, now(), now(), 1, :organization_id, :site_id, :code, :name,
                'main', false, true
            )
            ON CONFLICT (organization_id, code) DO NOTHING
            """
        ),
        {
            "id": str(uuid4()),
            "organization_id": str(organization_id),
            "site_id": str(site_id),
            "code": code,
            "name": name,
        },
    )


def ensure_unit(
    bind: sa.Connection,
    organization_id: object,
    code: str,
    name: str,
    symbol: str,
    precision: int,
) -> None:
    row = bind.execute(
        sa.text(
            """
            SELECT id, deleted_at
            FROM inventory_units
            WHERE code = :code
            ORDER BY deleted_at IS NULL DESC, created_at ASC, id ASC
            LIMIT 1
            """
        ),
        {"code": code},
    ).one_or_none()
    if row is not None:
        return
    bind.execute(
        sa.text(
            """
            INSERT INTO inventory_units
                (
                    id, created_at, updated_at, version, organization_id, code, name,
                    symbol, precision, is_active
                )
            VALUES (
                :id, now(), now(), 1, :organization_id, :code, :name, :symbol,
                :precision, true
            )
            ON CONFLICT (organization_id, code) DO NOTHING
            """
        ),
        {
            "id": str(uuid4()),
            "organization_id": str(organization_id),
            "code": code,
            "name": name,
            "symbol": symbol,
            "precision": precision,
        },
    )
