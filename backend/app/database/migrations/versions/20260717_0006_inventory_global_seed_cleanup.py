"""Globally merge duplicated inventory seed records.

Revision ID: 20260717_0006
Revises: 20260717_0005
Create Date: 2026-07-17 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0006"
down_revision: str | None = "20260717_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    repair_seed_names(bind)
    create_site_merge_map(bind)
    create_warehouse_merge_map(bind)
    merge_location_references(bind)
    merge_warehouse_references(bind)
    merge_site_references(bind)
    normalize_seed_keepers(bind)


def downgrade() -> None:
    pass


def repair_seed_names(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Київ', updated_at = now(), version = version + 1
            WHERE code = 'KYIV' AND name <> 'Київ'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Тальне', updated_at = now(), version = version + 1
            WHERE code = 'TALNE' AND name <> 'Тальне'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses
            SET name = 'Склад Київ', updated_at = now(), version = version + 1
            WHERE code IN ('KYIV-MAIN', 'MAIN') AND name <> 'Склад Київ'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses
            SET name = 'Склад Тальне', updated_at = now(), version = version + 1
            WHERE code = 'TALNE-MAIN' AND name <> 'Склад Тальне'
            """
        )
    )


def create_site_merge_map(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_global_site_merge ON COMMIT DROP AS
            WITH site_usage AS (
                SELECT
                    site.id,
                    site.code,
                    coalesce(count(DISTINCT warehouse.id), 0) AS warehouse_count,
                    coalesce(count(DISTINCT movement.id), 0) AS movement_count,
                    coalesce(count(DISTINCT balance.id), 0) AS balance_count,
                    coalesce(count(DISTINCT document.id), 0) AS document_count,
                    coalesce(count(DISTINCT site_scope.id), 0) AS scope_count,
                    site.deleted_at,
                    site.created_at
                FROM inventory_sites site
                LEFT JOIN inventory_warehouses warehouse ON warehouse.site_id = site.id
                LEFT JOIN inventory_movements movement ON movement.warehouse_id = warehouse.id
                LEFT JOIN inventory_stock_balances balance ON balance.warehouse_id = warehouse.id
                LEFT JOIN inventory_documents document
                    ON document.source_warehouse_id = warehouse.id
                    OR document.destination_warehouse_id = warehouse.id
                LEFT JOIN user_site_access site_scope ON site_scope.site_id = site.id
                WHERE site.code IN ('KYIV', 'TALNE')
                GROUP BY site.id
            ),
            ranked AS (
                SELECT
                    id,
                    code,
                    first_value(id) OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            movement_count DESC,
                            balance_count DESC,
                            document_count DESC,
                            warehouse_count DESC,
                            scope_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            movement_count DESC,
                            balance_count DESC,
                            document_count DESC,
                            warehouse_count DESC,
                            scope_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM site_usage
            )
            SELECT id AS duplicate_id, keeper_id, code
            FROM ranked
            WHERE row_number > 1
            """
        )
    )


def create_warehouse_merge_map(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_global_warehouse_merge ON COMMIT DROP AS
            WITH warehouse_usage AS (
                SELECT
                    warehouse.id,
                    CASE
                        WHEN warehouse.code = 'MAIN' THEN 'KYIV-MAIN'
                        ELSE warehouse.code
                    END AS target_code,
                    CASE
                        WHEN warehouse.code IN ('MAIN', 'KYIV-MAIN') THEN 'Склад Київ'
                        ELSE 'Склад Тальне'
                    END AS target_name,
                    coalesce(count(DISTINCT movement.id), 0) AS movement_count,
                    coalesce(count(DISTINCT balance.id), 0) AS balance_count,
                    coalesce(count(DISTINCT location.id), 0) AS location_count,
                    coalesce(count(DISTINCT document.id), 0) AS document_count,
                    coalesce(count(DISTINCT warehouse_scope.id), 0) AS scope_count,
                    warehouse.deleted_at,
                    warehouse.created_at
                FROM inventory_warehouses warehouse
                LEFT JOIN inventory_movements movement ON movement.warehouse_id = warehouse.id
                LEFT JOIN inventory_stock_balances balance ON balance.warehouse_id = warehouse.id
                LEFT JOIN inventory_storage_locations location
                    ON location.warehouse_id = warehouse.id
                LEFT JOIN inventory_documents document
                    ON document.source_warehouse_id = warehouse.id
                    OR document.destination_warehouse_id = warehouse.id
                LEFT JOIN user_warehouse_access warehouse_scope
                    ON warehouse_scope.warehouse_id = warehouse.id
                WHERE warehouse.code IN ('KYIV-MAIN', 'TALNE-MAIN', 'MAIN')
                GROUP BY warehouse.id
            ),
            ranked AS (
                SELECT
                    id,
                    target_code,
                    target_name,
                    first_value(id) OVER (
                        PARTITION BY target_code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            movement_count DESC,
                            balance_count DESC,
                            document_count DESC,
                            location_count DESC,
                            scope_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY target_code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            movement_count DESC,
                            balance_count DESC,
                            document_count DESC,
                            location_count DESC,
                            scope_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM warehouse_usage
            )
            SELECT id AS duplicate_id, keeper_id, target_code, target_name
            FROM ranked
            WHERE row_number > 1
            """
        )
    )


def merge_location_references(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_global_location_merge ON COMMIT DROP AS
            WITH warehouse_targets AS (
                SELECT duplicate_id AS warehouse_id, keeper_id AS target_warehouse_id
                FROM inventory_global_warehouse_merge
                UNION
                SELECT DISTINCT keeper_id AS warehouse_id, keeper_id AS target_warehouse_id
                FROM inventory_global_warehouse_merge
            ),
            location_targets AS (
                SELECT
                    location.id,
                    warehouse_targets.target_warehouse_id,
                    location.code,
                    location.created_at,
                    location.deleted_at
                FROM inventory_storage_locations location
                JOIN warehouse_targets ON warehouse_targets.warehouse_id = location.warehouse_id
            ),
            ranked AS (
                SELECT
                    id,
                    first_value(id) OVER (
                        PARTITION BY target_warehouse_id, code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY target_warehouse_id, code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM location_targets
            )
            SELECT id AS duplicate_id, keeper_id
            FROM ranked
            WHERE row_number > 1
            """
        )
    )
    merge_stock_balances_by_location(bind)
    bind.execute(
        sa.text(
            """
            UPDATE inventory_document_lines line
            SET
                source_location_id = location_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_location_merge location_merge
            WHERE line.source_location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_document_lines line
            SET
                destination_location_id = location_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_location_merge location_merge
            WHERE line.destination_location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_movements movement
            SET location_id = location_merge.keeper_id
            FROM inventory_global_location_merge location_merge
            WHERE movement.location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_serials serial
            SET
                current_location_id = location_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_location_merge location_merge
            WHERE serial.current_location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET parent_id = location_merge.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_global_location_merge location_merge
            WHERE location.parent_id = location_merge.duplicate_id
              AND location.id <> location_merge.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_storage_locations location
            USING inventory_global_location_merge location_merge
            WHERE location.id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET warehouse_id = warehouse_merge.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE location.warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )


def merge_warehouse_references(bind: sa.Connection) -> None:
    merge_stock_balances_by_warehouse(bind)
    bind.execute(
        sa.text(
            """
            DELETE FROM user_warehouse_access duplicate_access
            USING inventory_global_warehouse_merge warehouse_merge,
                  user_warehouse_access keeper_access
            WHERE duplicate_access.warehouse_id = warehouse_merge.duplicate_id
              AND keeper_access.user_id = duplicate_access.user_id
              AND keeper_access.warehouse_id = warehouse_merge.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE user_warehouse_access access
            SET warehouse_id = warehouse_merge.keeper_id
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE access.warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_items item
            SET
                default_warehouse_id = warehouse_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE item.default_warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_serials serial
            SET
                current_warehouse_id = warehouse_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE serial.current_warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_documents document
            SET
                source_warehouse_id = warehouse_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE document.source_warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_documents document
            SET
                destination_warehouse_id = warehouse_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE document.destination_warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_movements movement
            SET warehouse_id = warehouse_merge.keeper_id
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE movement.warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_warehouses warehouse
            USING inventory_global_warehouse_merge warehouse_merge
            WHERE warehouse.id = warehouse_merge.duplicate_id
            """
        )
    )


def merge_site_references(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM user_site_access duplicate_access
            USING inventory_global_site_merge site_merge, user_site_access keeper_access
            WHERE duplicate_access.site_id = site_merge.duplicate_id
              AND keeper_access.user_id = duplicate_access.user_id
              AND keeper_access.site_id = site_merge.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE user_site_access access
            SET site_id = site_merge.keeper_id
            FROM inventory_global_site_merge site_merge
            WHERE access.site_id = site_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses warehouse
            SET site_id = site_merge.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_global_site_merge site_merge
            WHERE warehouse.site_id = site_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_sites site
            USING inventory_global_site_merge site_merge
            WHERE site.id = site_merge.duplicate_id
            """
        )
    )


def normalize_seed_keepers(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Київ', updated_at = now(), version = version + 1
            WHERE code = 'KYIV'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_sites
            SET name = 'Тальне', updated_at = now(), version = version + 1
            WHERE code = 'TALNE'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_warehouses warehouse
            SET
                code = warehouse_merge.target_code,
                name = warehouse_merge.target_name,
                updated_at = now(),
                version = version + 1
            FROM (
                SELECT DISTINCT keeper_id, target_code, target_name
                FROM inventory_global_warehouse_merge
            ) warehouse_merge
            WHERE warehouse.id = warehouse_merge.keeper_id
            """
        )
    )


def merge_stock_balances_by_location(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances keeper
            SET quantity = keeper.quantity + duplicate.quantity, updated_at = now()
            FROM inventory_stock_balances duplicate, inventory_global_location_merge location_merge
            WHERE duplicate.location_id = location_merge.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = duplicate.warehouse_id
              AND keeper.location_id = location_merge.keeper_id
              AND keeper.lot_id IS NOT DISTINCT FROM duplicate.lot_id
              AND keeper.serial_id IS NOT DISTINCT FROM duplicate.serial_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_stock_balances duplicate
            USING inventory_stock_balances keeper, inventory_global_location_merge location_merge
            WHERE duplicate.location_id = location_merge.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = duplicate.warehouse_id
              AND keeper.location_id = location_merge.keeper_id
              AND keeper.lot_id IS NOT DISTINCT FROM duplicate.lot_id
              AND keeper.serial_id IS NOT DISTINCT FROM duplicate.serial_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances balance
            SET location_id = location_merge.keeper_id, updated_at = now()
            FROM inventory_global_location_merge location_merge
            WHERE balance.location_id = location_merge.duplicate_id
            """
        )
    )


def merge_stock_balances_by_warehouse(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances keeper
            SET quantity = keeper.quantity + duplicate.quantity, updated_at = now()
            FROM inventory_stock_balances duplicate,
                 inventory_global_warehouse_merge warehouse_merge
            WHERE duplicate.warehouse_id = warehouse_merge.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = warehouse_merge.keeper_id
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
            USING inventory_stock_balances keeper, inventory_global_warehouse_merge warehouse_merge
            WHERE duplicate.warehouse_id = warehouse_merge.duplicate_id
              AND keeper.organization_id = duplicate.organization_id
              AND keeper.item_id = duplicate.item_id
              AND keeper.warehouse_id = warehouse_merge.keeper_id
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
            SET warehouse_id = warehouse_merge.keeper_id, updated_at = now()
            FROM inventory_global_warehouse_merge warehouse_merge
            WHERE balance.warehouse_id = warehouse_merge.duplicate_id
            """
        )
    )
