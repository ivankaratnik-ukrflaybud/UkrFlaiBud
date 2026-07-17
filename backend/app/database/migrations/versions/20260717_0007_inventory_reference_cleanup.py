"""Clean duplicated inventory reference records.

Revision ID: 20260717_0007
Revises: 20260717_0006
Create Date: 2026-07-17 18:00:00.000000

"""

import importlib
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0007"
down_revision: str | None = "20260717_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


COMMON_UNIT_VALUES = """
    ('PCS', 'штука', 'шт', 0),
    ('SET', 'комплект', 'компл.', 0),
    ('M', 'метр', 'м', 3),
    ('M2', 'квадратний метр', 'м²', 3),
    ('KG', 'кілограм', 'кг', 3),
    ('G', 'грам', 'г', 3),
    ('L', 'літр', 'л', 3),
    ('PACK', 'упаковка', 'уп.', 0)
"""


def upgrade() -> None:
    bind = op.get_bind()
    drop_temp_tables(bind)
    rerun_seed_site_warehouse_cleanup(bind)
    create_unit_merge_map(bind)
    merge_unit_references(bind)
    normalize_common_units(bind)
    create_category_merge_map(bind)
    merge_category_references(bind)
    repair_category_encoding(bind)
    create_location_merge_map(bind)
    merge_location_references(bind)


def downgrade() -> None:
    pass


def drop_temp_tables(bind: sa.Connection) -> None:
    for table_name in (
        "inventory_global_site_merge",
        "inventory_global_warehouse_merge",
        "inventory_global_location_merge",
        "inventory_reference_unit_merge",
        "inventory_reference_category_merge",
        "inventory_reference_location_merge",
    ):
        bind.execute(sa.text(f"DROP TABLE IF EXISTS {table_name}"))


def rerun_seed_site_warehouse_cleanup(bind: sa.Connection) -> None:
    cleanup = importlib.import_module(
        "app.database.migrations.versions.20260717_0006_inventory_global_seed_cleanup"
    )
    cleanup.repair_seed_names(bind)
    cleanup.create_site_merge_map(bind)
    cleanup.create_warehouse_merge_map(bind)
    cleanup.merge_location_references(bind)
    cleanup.merge_warehouse_references(bind)
    cleanup.merge_site_references(bind)
    cleanup.normalize_seed_keepers(bind)


def create_unit_merge_map(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            f"""
            CREATE TEMP TABLE inventory_reference_unit_merge ON COMMIT DROP AS
            WITH seeded_units(code, canonical_name, canonical_symbol, canonical_precision) AS (
                VALUES {COMMON_UNIT_VALUES}
            ),
            unit_usage AS (
                SELECT
                    unit.id,
                    unit.code,
                    unit.deleted_at,
                    unit.is_active,
                    unit.created_at,
                    seeded_units.canonical_name,
                    seeded_units.canonical_symbol,
                    seeded_units.canonical_precision,
                    (
                        unit.name = seeded_units.canonical_name
                        AND unit.symbol = seeded_units.canonical_symbol
                        AND unit.precision = seeded_units.canonical_precision
                    ) AS is_canonical,
                    coalesce(count(item.id), 0) AS item_count
                FROM inventory_units unit
                JOIN seeded_units ON seeded_units.code = unit.code
                LEFT JOIN inventory_items item ON item.unit_of_measure_id = unit.id
                GROUP BY
                    unit.id,
                    seeded_units.canonical_name,
                    seeded_units.canonical_symbol,
                    seeded_units.canonical_precision
            ),
            ranked AS (
                SELECT
                    id,
                    code,
                    canonical_name,
                    canonical_symbol,
                    canonical_precision,
                    first_value(id) OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            is_canonical DESC,
                            item_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            is_canonical DESC,
                            item_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM unit_usage
            )
            SELECT
                id AS duplicate_id,
                keeper_id,
                code,
                canonical_name,
                canonical_symbol,
                canonical_precision
            FROM ranked
            WHERE row_number > 1
            """
        )
    )


def merge_unit_references(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_items item
            SET
                unit_of_measure_id = unit_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_reference_unit_merge unit_merge
            WHERE item.unit_of_measure_id = unit_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_units unit
            USING inventory_reference_unit_merge unit_merge
            WHERE unit.id = unit_merge.duplicate_id
            """
        )
    )


def normalize_common_units(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            f"""
            WITH seeded_units(code, canonical_name, canonical_symbol, canonical_precision) AS (
                VALUES {COMMON_UNIT_VALUES}
            )
            UPDATE inventory_units unit
            SET
                name = seeded_units.canonical_name,
                symbol = seeded_units.canonical_symbol,
                precision = seeded_units.canonical_precision,
                updated_at = now(),
                version = unit.version + 1
            FROM seeded_units
            WHERE unit.code = seeded_units.code
              AND (
                  unit.name <> seeded_units.canonical_name
                  OR unit.symbol <> seeded_units.canonical_symbol
                  OR unit.precision <> seeded_units.canonical_precision
              )
            """
        )
    )


def create_category_merge_map(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_reference_category_merge ON COMMIT DROP AS
            WITH duplicated_codes AS (
                SELECT code
                FROM inventory_item_categories
                GROUP BY code
                HAVING count(*) > 1
            ),
            category_usage AS (
                SELECT
                    category.id,
                    category.code,
                    category.deleted_at,
                    category.is_active,
                    category.created_at,
                    category.name !~ '^\\?+$' AS has_readable_name,
                    coalesce(count(DISTINCT item.id), 0) AS item_count,
                    coalesce(count(DISTINCT child.id), 0) AS child_count
                FROM inventory_item_categories category
                JOIN duplicated_codes ON duplicated_codes.code = category.code
                LEFT JOIN inventory_items item ON item.category_id = category.id
                LEFT JOIN inventory_item_categories child ON child.parent_id = category.id
                GROUP BY category.id
            ),
            ranked AS (
                SELECT
                    id,
                    code,
                    first_value(id) OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            item_count DESC,
                            child_count DESC,
                            has_readable_name DESC,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            item_count DESC,
                            child_count DESC,
                            has_readable_name DESC,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM category_usage
            )
            SELECT id AS duplicate_id, keeper_id, code
            FROM ranked
            WHERE row_number > 1
            """
        )
    )


def merge_category_references(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_items item
            SET
                category_id = category_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_reference_category_merge category_merge
            WHERE item.category_id = category_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_item_categories keeper
            SET parent_id = NULL, updated_at = now(), version = version + 1
            FROM inventory_reference_category_merge category_merge
            WHERE keeper.id = category_merge.keeper_id
              AND keeper.parent_id = category_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_item_categories category
            SET
                parent_id = category_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_reference_category_merge category_merge
            WHERE category.parent_id = category_merge.duplicate_id
              AND category.id <> category_merge.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_item_categories category
            USING inventory_reference_category_merge category_merge
            WHERE category.id = category_merge.duplicate_id
            """
        )
    )


def repair_category_encoding(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_item_categories
            SET name = 'Електроніка', updated_at = now(), version = version + 1
            WHERE code = 'ELEC' AND name ~ '^\\?+$'
            """
        )
    )


def create_location_merge_map(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE inventory_reference_location_merge ON COMMIT DROP AS
            WITH duplicated_locations AS (
                SELECT warehouse_id, code
                FROM inventory_storage_locations
                GROUP BY warehouse_id, code
                HAVING count(*) > 1
            ),
            location_usage AS (
                SELECT
                    location.id,
                    location.warehouse_id,
                    location.code,
                    location.deleted_at,
                    location.is_active,
                    location.created_at,
                    coalesce(count(DISTINCT movement.id), 0) AS movement_count,
                    coalesce(count(DISTINCT balance.id), 0) AS balance_count,
                    coalesce(count(DISTINCT serial.id), 0) AS serial_count,
                    coalesce(count(DISTINCT child.id), 0) AS child_count,
                    coalesce(count(DISTINCT line_source.id), 0)
                        + coalesce(count(DISTINCT line_destination.id), 0) AS line_count
                FROM inventory_storage_locations location
                JOIN duplicated_locations
                    ON duplicated_locations.warehouse_id = location.warehouse_id
                    AND duplicated_locations.code = location.code
                LEFT JOIN inventory_movements movement ON movement.location_id = location.id
                LEFT JOIN inventory_stock_balances balance ON balance.location_id = location.id
                LEFT JOIN inventory_serials serial ON serial.current_location_id = location.id
                LEFT JOIN inventory_storage_locations child ON child.parent_id = location.id
                LEFT JOIN inventory_document_lines line_source
                    ON line_source.source_location_id = location.id
                LEFT JOIN inventory_document_lines line_destination
                    ON line_destination.destination_location_id = location.id
                GROUP BY location.id
            ),
            ranked AS (
                SELECT
                    id,
                    first_value(id) OVER (
                        PARTITION BY warehouse_id, code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            movement_count DESC,
                            balance_count DESC,
                            line_count DESC,
                            serial_count DESC,
                            child_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS keeper_id,
                    row_number() OVER (
                        PARTITION BY warehouse_id, code
                        ORDER BY
                            deleted_at IS NOT NULL,
                            is_active DESC,
                            movement_count DESC,
                            balance_count DESC,
                            line_count DESC,
                            serial_count DESC,
                            child_count DESC,
                            created_at ASC,
                            id ASC
                    ) AS row_number
                FROM location_usage
            )
            SELECT id AS duplicate_id, keeper_id
            FROM ranked
            WHERE row_number > 1
            """
        )
    )


def merge_location_references(bind: sa.Connection) -> None:
    merge_stock_balances_by_location(bind)
    bind.execute(
        sa.text(
            """
            UPDATE inventory_document_lines line
            SET
                source_location_id = location_merge.keeper_id,
                updated_at = now(),
                version = version + 1
            FROM inventory_reference_location_merge location_merge
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
            FROM inventory_reference_location_merge location_merge
            WHERE line.destination_location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_movements movement
            SET location_id = location_merge.keeper_id
            FROM inventory_reference_location_merge location_merge
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
            FROM inventory_reference_location_merge location_merge
            WHERE serial.current_location_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET parent_id = NULL, updated_at = now(), version = version + 1
            FROM inventory_reference_location_merge location_merge
            WHERE location.id = location_merge.keeper_id
              AND location.parent_id = location_merge.duplicate_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET parent_id = location_merge.keeper_id, updated_at = now(), version = version + 1
            FROM inventory_reference_location_merge location_merge
            WHERE location.parent_id = location_merge.duplicate_id
              AND location.id <> location_merge.keeper_id
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_storage_locations location
            USING inventory_reference_location_merge location_merge
            WHERE location.id = location_merge.duplicate_id
            """
        )
    )


def merge_stock_balances_by_location(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_stock_balances keeper
            SET quantity = keeper.quantity + duplicate.quantity, updated_at = now()
            FROM inventory_stock_balances duplicate,
                 inventory_reference_location_merge location_merge
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
            USING inventory_stock_balances keeper, inventory_reference_location_merge location_merge
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
            FROM inventory_reference_location_merge location_merge
            WHERE balance.location_id = location_merge.duplicate_id
            """
        )
    )
