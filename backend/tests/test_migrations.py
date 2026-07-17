import asyncio
import importlib
import os
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

import app.core.config as config_module
from app.core.config import get_settings


def alembic_config(database_url: str) -> Config:
    config_path = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


async def reset_public_schema(database_url: str) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


async def table_names(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    await engine.dispose()
    return set(names)


async def execute_sql(database_url: str, statements: list[tuple[str, dict[str, object]]]) -> None:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        for statement, params in statements:
            await connection.execute(text(statement), params)
    await engine.dispose()


async def fetch_all(
    database_url: str, statement: str, params: dict[str, object] | None = None
) -> list[tuple[object, ...]]:
    engine = create_async_engine(database_url)
    async with engine.connect() as connection:
        rows = (await connection.execute(text(statement), params or {})).all()
    await engine.dispose()
    return [tuple(row) for row in rows]


def test_alembic_upgrade_downgrade_and_reupgrade(disposable_database: str) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)

    command.upgrade(config, "head")
    names_after_upgrade = asyncio.run(table_names(disposable_database))
    assert {
        "audit_log",
        "outbox_event",
        "organizations",
        "departments",
        "positions",
        "employees",
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "user_sessions",
        "login_attempts",
        "password_reset_tokens",
        "inventory_sites",
        "inventory_warehouses",
        "inventory_storage_locations",
        "inventory_units",
        "inventory_item_categories",
        "inventory_items",
        "inventory_documents",
        "inventory_movements",
        "inventory_stock_balances",
        "user_site_access",
        "user_warehouse_access",
        "alembic_version",
    }.issubset(names_after_upgrade)

    command.downgrade(config, "base")
    names_after_downgrade = asyncio.run(table_names(disposable_database))
    assert "audit_log" not in names_after_downgrade
    assert "outbox_event" not in names_after_downgrade
    assert "organizations" not in names_after_downgrade
    assert "users" not in names_after_downgrade
    assert "inventory_sites" not in names_after_downgrade

    command.upgrade(config, "head")
    names_after_reupgrade = asyncio.run(table_names(disposable_database))
    assert {
        "audit_log",
        "outbox_event",
        "organizations",
        "departments",
        "positions",
        "employees",
        "users",
        "roles",
        "permissions",
        "user_roles",
        "role_permissions",
        "user_sessions",
        "login_attempts",
        "password_reset_tokens",
        "inventory_sites",
        "inventory_warehouses",
        "inventory_storage_locations",
        "inventory_units",
        "inventory_item_categories",
        "inventory_items",
        "inventory_documents",
        "inventory_movements",
        "inventory_stock_balances",
        "user_site_access",
        "user_warehouse_access",
        "alembic_version",
    }.issubset(names_after_reupgrade)


def test_inventory_seed_is_idempotent(disposable_database: str) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)
    organization_id = str(uuid4())

    command.upgrade(config, "20260716_0003")
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Seed Test', 'Seed', 'Seed Test LLC', '12345678', true)
                    """,
                    {"id": organization_id},
                )
            ],
        )
    )

    command.upgrade(config, "20260717_0004")
    inventory_seed_migration = importlib.import_module(
        "app.database.migrations.versions.20260717_0004_inventory"
    )

    engine_url = disposable_database
    engine = create_async_engine(engine_url)

    async def run_seed_twice() -> None:
        async with engine.begin() as connection:
            await connection.run_sync(inventory_seed_migration.seed_initial_inventory_data)
            await connection.run_sync(inventory_seed_migration.seed_initial_inventory_data)
        await engine.dispose()

    asyncio.run(run_seed_twice())

    rows = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, count(*)
            FROM inventory_sites
            WHERE organization_id = :organization_id
            GROUP BY code
            ORDER BY code
            """,
            {"organization_id": organization_id},
        )
    )
    assert rows == [("KYIV", 1), ("TALNE", 1)]
    warehouse_rows = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, count(*)
            FROM inventory_warehouses
            WHERE organization_id = :organization_id
            GROUP BY code
            ORDER BY code
            """,
            {"organization_id": organization_id},
        )
    )
    assert warehouse_rows == [("KYIV-MAIN", 1), ("TALNE-MAIN", 1)]


def test_inventory_seed_cleanup_merges_duplicate_seeded_records(
    disposable_database: str,
) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)

    organization_id = str(uuid4())
    duplicate_site_id = str(uuid4())
    duplicate_warehouse_id = str(uuid4())
    category_id = str(uuid4())
    unit_id = str(uuid4())
    item_id = str(uuid4())
    stock_id = str(uuid4())

    command.upgrade(config, "20260716_0003")
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Cleanup Test', 'Cleanup', 'Cleanup Test LLC', '87654321', true)
                    """,
                    {"id": organization_id},
                )
            ],
        )
    )
    command.upgrade(config, "20260717_0004")
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    "ALTER TABLE inventory_sites "
                    "DROP CONSTRAINT uq_inventory_sites_organization_code",
                    {},
                ),
                (
                    "ALTER TABLE inventory_warehouses "
                    "DROP CONSTRAINT uq_inventory_warehouses_organization_code",
                    {},
                ),
                (
                    """
                    INSERT INTO inventory_sites
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'KYIV', '????', true)
                    """,
                    {"id": duplicate_site_id, "organization_id": organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_warehouses
                        (
                            id, organization_id, site_id, code, name, warehouse_type,
                            allow_negative_stock, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :site_id, 'KYIV-MAIN', '????? ????',
                            'main', false, true
                        )
                    """,
                    {
                        "id": duplicate_warehouse_id,
                        "organization_id": organization_id,
                        "site_id": duplicate_site_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_units
                        (id, organization_id, code, name, symbol, precision, is_active)
                    VALUES
                        (:id, :organization_id, 'TEST', 'тест', 'т', 0, true)
                    """,
                    {"id": unit_id, "organization_id": organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_item_categories
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'TEST', 'Тест', true)
                    """,
                    {"id": category_id, "organization_id": organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_items
                        (
                            id, organization_id, sku, name, category_id, unit_of_measure_id,
                            item_type, default_warehouse_id, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, 'TEST-1', 'Тестова позиція',
                            :category_id, :unit_id, 'component', :warehouse_id, true
                        )
                    """,
                    {
                        "id": item_id,
                        "organization_id": organization_id,
                        "category_id": category_id,
                        "unit_id": unit_id,
                        "warehouse_id": duplicate_warehouse_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_stock_balances
                        (id, organization_id, item_id, warehouse_id, quantity)
                    VALUES
                        (:id, :organization_id, :item_id, :warehouse_id, 7)
                    """,
                    {
                        "id": stock_id,
                        "organization_id": organization_id,
                        "item_id": item_id,
                        "warehouse_id": duplicate_warehouse_id,
                    },
                ),
            ],
        )
    )

    command.upgrade(config, "head")

    site_rows = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, count(*)
            FROM inventory_sites
            WHERE organization_id = :organization_id AND code = 'KYIV'
            GROUP BY code, name
            """,
            {"organization_id": organization_id},
        )
    )
    assert site_rows == [("KYIV", "Київ", 1)]

    warehouse_rows = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, count(*)
            FROM inventory_warehouses
            WHERE organization_id = :organization_id AND code = 'KYIV-MAIN'
            GROUP BY code, name
            """,
            {"organization_id": organization_id},
        )
    )
    assert warehouse_rows == [("KYIV-MAIN", "Склад Київ", 1)]

    references = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT item.default_warehouse_id = balance.warehouse_id, balance.quantity
            FROM inventory_items item
            JOIN inventory_stock_balances balance ON balance.item_id = item.id
            WHERE item.id = :item_id
            """,
            {"item_id": item_id},
        )
    )
    assert references == [(True, 7)]


def test_inventory_global_seed_cleanup_removes_cross_organization_duplicates(
    disposable_database: str,
) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)

    first_organization_id = str(uuid4())
    second_organization_id = str(uuid4())
    second_kyiv_site_id = str(uuid4())
    second_talne_site_id = str(uuid4())
    first_main_warehouse_id = str(uuid4())
    second_kyiv_warehouse_id = str(uuid4())
    second_talne_warehouse_id = str(uuid4())
    second_main_warehouse_id = str(uuid4())

    command.upgrade(config, "20260716_0003")
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Global Seed A', 'GSA', 'Global Seed A LLC', '11111111', true)
                    """,
                    {"id": first_organization_id},
                ),
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Global Seed B', 'GSB', 'Global Seed B LLC', '22222222', true)
                    """,
                    {"id": second_organization_id},
                ),
            ],
        )
    )

    command.upgrade(config, "20260717_0005")
    first_kyiv_site_row = asyncio.run(
        fetch_all(
            disposable_database,
            "SELECT id, organization_id FROM inventory_sites WHERE code = 'KYIV'",
        )
    )[0]
    first_kyiv_site_id = first_kyiv_site_row[0]
    seeded_organization_id = first_kyiv_site_row[1]
    duplicate_organization_id = (
        second_organization_id
        if str(seeded_organization_id) == first_organization_id
        else first_organization_id
    )
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    """
                    INSERT INTO inventory_sites
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'KYIV', 'Kyiv', true)
                    """,
                    {"id": second_kyiv_site_id, "organization_id": duplicate_organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_sites
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'TALNE', '??????', true)
                    """,
                    {"id": second_talne_site_id, "organization_id": duplicate_organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_warehouses
                        (
                            id, organization_id, site_id, code, name, warehouse_type,
                            allow_negative_stock, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :site_id, 'MAIN', 'Main',
                            'main', false, true
                        )
                    """,
                    {
                        "id": first_main_warehouse_id,
                        "organization_id": seeded_organization_id,
                        "site_id": first_kyiv_site_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_warehouses
                        (
                            id, organization_id, site_id, code, name, warehouse_type,
                            allow_negative_stock, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :site_id, 'KYIV-MAIN',
                            '????? ????', 'main', false, true
                        )
                    """,
                    {
                        "id": second_kyiv_warehouse_id,
                        "organization_id": duplicate_organization_id,
                        "site_id": second_kyiv_site_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_warehouses
                        (
                            id, organization_id, site_id, code, name, warehouse_type,
                            allow_negative_stock, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :site_id, 'TALNE-MAIN',
                            '????? ??????', 'main', false, true
                        )
                    """,
                    {
                        "id": second_talne_warehouse_id,
                        "organization_id": duplicate_organization_id,
                        "site_id": second_talne_site_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_warehouses
                        (
                            id, organization_id, site_id, code, name, warehouse_type,
                            allow_negative_stock, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :site_id, 'MAIN', 'Main',
                            'main', false, true
                        )
                    """,
                    {
                        "id": second_main_warehouse_id,
                        "organization_id": duplicate_organization_id,
                        "site_id": second_kyiv_site_id,
                    },
                ),
            ],
        )
    )

    command.upgrade(config, "head")

    site_counts = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, count(*)
            FROM inventory_sites
            WHERE code IN ('KYIV', 'TALNE')
            GROUP BY code, name
            ORDER BY code
            """,
        )
    )
    assert site_counts == [("KYIV", "Київ", 1), ("TALNE", "Тальне", 1)]

    warehouse_counts = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, count(*)
            FROM inventory_warehouses
            WHERE code IN ('KYIV-MAIN', 'TALNE-MAIN', 'MAIN')
            GROUP BY code, name
            ORDER BY code
            """,
        )
    )
    assert warehouse_counts == [
        ("KYIV-MAIN", "Склад Київ", 1),
        ("TALNE-MAIN", "Склад Тальне", 1),
    ]


def test_inventory_reference_cleanup_removes_seeded_lookup_duplicates(
    disposable_database: str,
) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)

    first_organization_id = str(uuid4())
    second_organization_id = str(uuid4())
    duplicate_unit_id = str(uuid4())
    duplicate_category_id = str(uuid4())
    keeper_category_id = str(uuid4())
    item_id = str(uuid4())
    first_location_id = str(uuid4())
    second_location_id = str(uuid4())
    stock_id = str(uuid4())

    command.upgrade(config, "20260716_0003")
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Reference Seed A', 'RSA', 'Reference Seed A LLC', '33333333', true)
                    """,
                    {"id": first_organization_id},
                ),
                (
                    """
                    INSERT INTO organizations
                        (id, name, short_name, legal_name, edrpou, is_active)
                    VALUES
                        (:id, 'Reference Seed B', 'RSB', 'Reference Seed B LLC', '44444444', true)
                    """,
                    {"id": second_organization_id},
                ),
            ],
        )
    )
    command.upgrade(config, "20260717_0006")

    canonical_unit_row = asyncio.run(
        fetch_all(
            disposable_database,
            "SELECT id, organization_id FROM inventory_units WHERE code = 'PCS'",
        )
    )[0]
    canonical_unit_id = canonical_unit_row[0]
    duplicate_unit_organization_id = (
        second_organization_id
        if str(canonical_unit_row[1]) != second_organization_id
        else first_organization_id
    )
    warehouse_id = asyncio.run(
        fetch_all(
            disposable_database,
            "SELECT id FROM inventory_warehouses WHERE code = 'KYIV-MAIN'",
        )
    )[0][0]
    asyncio.run(
        execute_sql(
            disposable_database,
            [
                (
                    "ALTER TABLE inventory_storage_locations "
                    "DROP CONSTRAINT uq_inventory_locations_warehouse_code",
                    {},
                ),
                (
                    "ALTER TABLE inventory_item_categories "
                    "DROP CONSTRAINT uq_inventory_categories_organization_code",
                    {},
                ),
                (
                    """
                    INSERT INTO inventory_units
                        (id, organization_id, code, name, symbol, precision, is_active)
                    VALUES
                        (:id, :organization_id, 'PCS', '?????', '??', 0, true)
                    """,
                    {
                        "id": duplicate_unit_id,
                        "organization_id": duplicate_unit_organization_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_item_categories
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'ELEC', '???????????', true)
                    """,
                    {"id": duplicate_category_id, "organization_id": first_organization_id},
                ),
                (
                    """
                    INSERT INTO inventory_item_categories
                        (id, organization_id, code, name, is_active)
                    VALUES
                        (:id, :organization_id, 'ELEC', '???????????', true)
                    """,
                    {
                        "id": keeper_category_id,
                        "organization_id": duplicate_unit_organization_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_items
                        (
                            id, organization_id, sku, name, category_id, unit_of_measure_id,
                            item_type, is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, 'REF-1', 'Reference item',
                            :category_id, :unit_id, 'component', true
                        )
                    """,
                    {
                        "id": item_id,
                        "organization_id": duplicate_unit_organization_id,
                        "category_id": keeper_category_id,
                        "unit_id": duplicate_unit_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_storage_locations
                        (
                            id, organization_id, warehouse_id, code, name, location_type,
                            is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :warehouse_id, 'A1', 'A1 duplicate',
                            'bin', true
                        )
                    """,
                    {
                        "id": first_location_id,
                        "organization_id": first_organization_id,
                        "warehouse_id": warehouse_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_storage_locations
                        (
                            id, organization_id, warehouse_id, code, name, location_type,
                            is_active
                        )
                    VALUES
                        (
                            :id, :organization_id, :warehouse_id, 'A1', 'A1 referenced',
                            'bin', true
                        )
                    """,
                    {
                        "id": second_location_id,
                        "organization_id": first_organization_id,
                        "warehouse_id": warehouse_id,
                    },
                ),
                (
                    """
                    INSERT INTO inventory_stock_balances
                        (id, organization_id, item_id, warehouse_id, location_id, quantity)
                    VALUES
                        (:id, :organization_id, :item_id, :warehouse_id, :location_id, 5)
                    """,
                    {
                        "id": stock_id,
                        "organization_id": duplicate_unit_organization_id,
                        "item_id": item_id,
                        "warehouse_id": warehouse_id,
                        "location_id": second_location_id,
                    },
                ),
            ],
        )
    )

    command.upgrade(config, "head")

    unit_counts = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, symbol, count(*)
            FROM inventory_units
            WHERE code IN ('PCS', 'SET', 'M', 'M2', 'KG', 'G', 'L', 'PACK')
            GROUP BY code, name, symbol
            ORDER BY code
            """,
        )
    )
    assert unit_counts == [
        ("G", "грам", "г", 1),
        ("KG", "кілограм", "кг", 1),
        ("L", "літр", "л", 1),
        ("M", "метр", "м", 1),
        ("M2", "квадратний метр", "м²", 1),
        ("PACK", "упаковка", "уп.", 1),
        ("PCS", "штука", "шт", 1),
        ("SET", "комплект", "компл.", 1),
    ]

    category_counts = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT code, name, count(*)
            FROM inventory_item_categories
            WHERE code = 'ELEC'
            GROUP BY code, name
            """,
        )
    )
    assert category_counts == [("ELEC", "Електроніка", 1)]

    references = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT
                item.unit_of_measure_id = :canonical_unit_id,
                category.code,
                balance.quantity
            FROM inventory_items item
            JOIN inventory_item_categories category ON category.id = item.category_id
            JOIN inventory_stock_balances balance ON balance.item_id = item.id
            WHERE item.id = :item_id
            """,
            {"item_id": item_id, "canonical_unit_id": canonical_unit_id},
        )
    )
    assert references == [(True, "ELEC", 5)]

    location_counts = asyncio.run(
        fetch_all(
            disposable_database,
            """
            SELECT warehouse_id, code, count(*)
            FROM inventory_storage_locations
            WHERE warehouse_id = :warehouse_id AND code = 'A1'
            GROUP BY warehouse_id, code
            """,
            {"warehouse_id": warehouse_id},
        )
    )
    assert location_counts == [(warehouse_id, "A1", 1)]
