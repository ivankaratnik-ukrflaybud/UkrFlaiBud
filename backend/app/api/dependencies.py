from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_factory() as session:
        yield session


async def get_unit_of_work() -> AsyncGenerator[SQLAlchemyUnitOfWork]:
    async with SQLAlchemyUnitOfWork() as unit_of_work:
        yield unit_of_work
