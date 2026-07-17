"""Clean duplicate seeded inventory records.

Revision ID: 20260717_0005
Revises: 20260717_0004
Create Date: 2026-07-17 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0005"
down_revision: str | None = "20260717_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    repair_bad_seed_names(bind)
    merge_duplicate_sites(bind)
    merge_duplicate_warehouses(bind)


def downgrade() -> None:
    pass


def repair_bad_seed_names(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Київ', updated_at = now(), version = version + 1
            WHERE code = 'KYIV' AND name IN ('????', 'РљРёС—РІ')
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Тальне', updated_at = now(), version = version + 1
            WHERE code = 'TALNE' AND name IN ('??????', 'РўР°Р»СЊРЅРµ')
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses
            SET name = 'Склад Київ', updated_at = now(), version = version + 1
            WHERE code = 'KYIV-MAIN' AND name IN ('????? ????', 'РЎРєР»Р°Рґ РљРёС—РІ')
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses
            SET name = 'Склад Тальне', updated_at = now(), version = version + 1
            WHERE code = 'TALNE-MAIN' AND name IN ('????? ??????', 'РЎРєР»Р°Рґ РўР°Р»СЊРЅРµ')
            """
        )
    )


def merge_duplicate_sites(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_site_seed_merge ON COMMIT DROP AS
            WITH ranked AS (
                SELECT
                    id,
                    first_value(id) OVER (
                        PARTITION BY organization_id, code
                        ORDER BY deleted_at IS NOT NULL, created_at ASC, id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY organization_id, code
                        ORDER BY deleted_at IS NOT NULL, created_at ASC, id ASC
                    ) AS row_number
                FROM inventory_sites
                WHERE code IN ('KYIV', 'TALNE')
            )
            SELECT id AS duplicate_id, keeper_id
            FROM ranked
            WHERE row_number > 1
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM user_site_access duplicate_access
            USING inventory_site_seed_merge merge_map, user_site_access keeper_access
            WHERE duplicate_access.site_id = merge_map.duplicate_id
              AND keeper_access.user_id = duplicate_access.user_id
              AND keeper_access.site_id = merge_map.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE user_site_access access
            SET site_id = merge_map.keeper_id
            FROM inventory_site_seed_merge merge_map
            WHERE access.site_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses warehouse
            SET site_id = merge_map.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_site_seed_merge merge_map
            WHERE warehouse.site_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_sites site
            USING inventory_site_seed_merge merge_map
            WHERE site.id = merge_map.duplicate_id
            """
        )
    )


def merge_duplicate_warehouses(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_warehouse_seed_merge ON COMMIT DROP AS
            WITH ranked AS (
                SELECT
                    id,
                    first_value(id) OVER (
                        PARTITION BY organization_id, code
                        ORDER BY deleted_at IS NOT NULL, created_at ASC, id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY organization_id, code
                        ORDER BY deleted_at IS NOT NULL, created_at ASC, id ASC
                    ) AS row_number
                FROM inventory_warehouses
                WHERE code IN ('KYIV-MAIN', 'TALNE-MAIN')
            )
            SELECT id AS duplicate_id, keeper_id
            FROM ranked
            WHERE row_number > 1
            """
        )
    )
    merge_stock_balances(bind)
    bind.execute(
        sa.text(
            """
            DELETE FROM user_warehouse_access duplicate_access
            USING inventory_warehouse_seed_merge merge_map, user_warehouse_access keeper_access
            WHERE duplicate_access.warehouse_id = merge_map.duplicate_id
              AND keeper_access.user_id = duplicate_access.user_id
              AND keeper_access.warehouse_id = merge_map.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE user_warehouse_access access
            SET warehouse_id = merge_map.keeper_id
            FROM inventory_warehouse_seed_merge merge_map
            WHERE access.warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_items item
            SET
                default_warehouse_id = merge_map.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_warehouse_seed_merge merge_map
            WHERE item.default_warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_serials serial
            SET
                current_warehouse_id = merge_map.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_warehouse_seed_merge merge_map
            WHERE serial.current_warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_documents document
            SET source_warehouse_id = merge_map.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_warehouse_seed_merge merge_map
            WHERE document.source_warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_documents document
            SET
                destination_warehouse_id = merge_map.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_warehouse_seed_merge merge_map
            WHERE document.destination_warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_movements movement
            SET warehouse_id = merge_map.keeper_id
            FROM inventory_warehouse_seed_merge merge_map
            WHERE movement.warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET warehouse_id = merge_map.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_warehouse_seed_merge merge_map
            WHERE location.warehouse_id = merge_map.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_warehouses warehouse
            USING inventory_warehouse_seed_merge merge_map
            WHERE warehouse.id = merge_map.duplicate_id
            """
        )
    )


def merge_stock_balances(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances keeper
            SET quantity = keeper.quantity + duplicate.quantity, updated_at = now()
            FROM inventory_stock_balances duplicate, inventory_warehouse_seed_merge merge_map
            WHERE duplicate.warehouse_id = merge_map.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = merge_map.keeper_id
              AND keeper.location_id IS NOT DISTINCT FROM duplicate.location_id
              AND keeper.lot_id IS NOT DISTINCT FROM duplicate.lot_id
              AND keeper.serial_id IS NOT DISTINCT FROM duplicate.serial_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_stock_balances duplicate
            USING inventory_stock_balances keeper, inventory_warehouse_seed_merge merge_map
            WHERE duplicate.warehouse_id = merge_map.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = merge_map.keeper_id
              AND keeper.location_id IS NOT DISTINCT FROM duplicate.location_id
              AND keeper.lot_id IS NOT DISTINCT FROM duplicate.lot_id
              AND keeper.serial_id IS NOT DISTINCT FROM duplicate.serial_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances balance
            SET warehouse_id = merge_map.keeper_id, updated_at = now()
            FROM inventory_warehouse_seed_merge merge_map
            WHERE balance.warehouse_id = merge_map.duplicate_id
            """
        )
    )
