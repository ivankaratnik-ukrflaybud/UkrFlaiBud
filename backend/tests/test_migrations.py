import asyncio
import os
from pathlib import Path

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


def test_alembic_upgrade_downgrade_and_reupgrade(disposable_database: str) -> None:
    asyncio.run(reset_public_schema(disposable_database))
    os.environ["DATABASE_URL"] = disposable_database
    get_settings.cache_clear()
    config_module.settings = get_settings()
    config = alembic_config(disposable_database)

    command.upgrade(config, "head")
    names_after_upgrade = asyncio.run(table_names(disposable_database))
    assert {"audit_log", "outbox_event", "alembic_version"}.issubset(names_after_upgrade)

    command.downgrade(config, "base")
    names_after_downgrade = asyncio.run(table_names(disposable_database))
    assert "audit_log" not in names_after_downgrade
    assert "outbox_event" not in names_after_downgrade

    command.upgrade(config, "head")
    names_after_reupgrade = asyncio.run(table_names(disposable_database))
    assert {"audit_log", "outbox_event", "alembic_version"}.issubset(names_after_reupgrade)
