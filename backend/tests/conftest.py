import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://ukrflybud:change-me@localhost:5432/ukrflybud_test",
)

from app.database.base import Base  # noqa: E402
from tests.support import TechnicalRecord  # noqa: E402, F401


@pytest.fixture(scope="session", autouse=True)
def disposable_database() -> Generator[str]:
    server_url = make_url(
        os.getenv(
            "TEST_DATABASE_SERVER_URL",
            "postgresql+asyncpg://ukrflybud:change-me@localhost:5432/postgres",
        )
    )
    database_name = f"ukrflybud_test_{uuid4().hex}"
    database_url = server_url.set(database=database_name)

    async def create_database() -> None:
        connection = await asyncpg.connect(
            user=server_url.username,
            password=server_url.password,
            host=server_url.host,
            port=server_url.port or 5432,
            database=server_url.database or "postgres",
        )
        try:
            await connection.execute(f'CREATE DATABASE "{database_name}"')
        finally:
            await connection.close()

    async def drop_database() -> None:
        connection = await asyncpg.connect(
            user=server_url.username,
            password=server_url.password,
            host=server_url.host,
            port=server_url.port or 5432,
            database=server_url.database or "postgres",
        )
        try:
            await connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1",
                database_name,
            )
            await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        finally:
            await connection.close()

    asyncio.run(create_database())
    os.environ["DATABASE_URL"] = database_url.render_as_string(hide_password=False)
    yield os.environ["DATABASE_URL"]
    asyncio.run(drop_database())


@pytest.fixture
async def async_engine(disposable_database: str) -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(disposable_database, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(async_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    async with async_engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
