from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from tests.support import TechnicalRecord


async def test_repository_create_get_update_soft_delete_and_list(db_session: AsyncSession) -> None:
    repository = SQLAlchemyRepository(db_session, TechnicalRecord)
    record = await repository.create(TechnicalRecord(name="first"))
    await db_session.commit()

    found = await repository.get(record.id)
    assert found is not None
    assert found.name == "first"

    found.name = "updated"
    await repository.update(found)
    await db_session.commit()

    updated = await repository.get(record.id)
    assert updated is not None
    assert updated.name == "updated"
    assert updated.version == 2

    await repository.soft_delete(record.id)
    await db_session.commit()

    assert await repository.get(record.id) is None
    assert await repository.get(record.id, include_deleted=True) is not None
    assert await repository.list() == []


async def test_unit_of_work_commit(async_engine) -> None:
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_engine.begin() as connection:
        await connection.run_sync(TechnicalRecord.metadata.drop_all)
        await connection.run_sync(TechnicalRecord.metadata.create_all)

    async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.session is not None
        repository = SQLAlchemyRepository(unit_of_work.session, TechnicalRecord)
        await repository.create(TechnicalRecord(name="committed"))
        await unit_of_work.commit()

    async with session_factory() as session:
        result = await session.scalar(
            select(TechnicalRecord).where(TechnicalRecord.name == "committed")
        )

    assert result is not None


async def test_unit_of_work_rollback(async_engine) -> None:
    session_factory = async_sessionmaker(async_engine, expire_on_commit=False)
    async with async_engine.begin() as connection:
        await connection.run_sync(TechnicalRecord.metadata.drop_all)
        await connection.run_sync(TechnicalRecord.metadata.create_all)

    async with SQLAlchemyUnitOfWork(session_factory) as unit_of_work:
        assert unit_of_work.session is not None
        repository = SQLAlchemyRepository(unit_of_work.session, TechnicalRecord)
        await repository.create(TechnicalRecord(name="rolled-back"))
        await unit_of_work.rollback()

    async with session_factory() as session:
        result = await session.scalar(
            select(TechnicalRecord).where(TechnicalRecord.name == "rolled-back")
        )

    assert result is None
