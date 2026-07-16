from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditAction, AuditLog
from app.database.outbox import OutboxEvent
from app.repositories.sqlalchemy_audit import SQLAlchemyAuditLogRepository
from app.repositories.sqlalchemy_outbox import SQLAlchemyOutboxRepository


async def test_audit_log_persistence(db_session: AsyncSession) -> None:
    repository = SQLAlchemyAuditLogRepository(db_session)
    entity_id = uuid4()

    audit_log = await repository.create(
        AuditLog(
            action=AuditAction.CREATE.value,
            entity_type="technical_record",
            entity_id=entity_id,
            actor_id=uuid4(),
            before_data=None,
            after_data={"name": "created"},
            correlation_id=uuid4(),
            ip_address="127.0.0.1",
            user_agent="pytest",
        )
    )
    await db_session.commit()

    found = await repository.get(audit_log.id)
    assert found is not None
    assert found.entity_id == entity_id
    assert found.after_data == {"name": "created"}


async def test_outbox_event_persistence_pending_and_mark_processed(
    db_session: AsyncSession,
) -> None:
    repository = SQLAlchemyOutboxRepository(db_session)
    event = await repository.create(
        OutboxEvent(
            event_type="technical.created",
            aggregate_type="technical_record",
            aggregate_id=uuid4(),
            payload={"ok": True},
            occurred_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    pending = await repository.list_pending()
    assert [item.id for item in pending] == [event.id]

    await repository.mark_processed(event.id)
    await db_session.commit()

    assert await repository.list_pending() == []


async def test_outbox_mark_failed(db_session: AsyncSession) -> None:
    repository = SQLAlchemyOutboxRepository(db_session)
    event = await repository.create(
        OutboxEvent(
            event_type="technical.failed",
            aggregate_type="technical_record",
            aggregate_id=uuid4(),
            payload={},
            occurred_at=datetime.now(UTC),
        )
    )
    await db_session.commit()

    await repository.mark_failed(event.id, "temporary error")
    await db_session.commit()

    found = await repository.get(event.id)
    assert found is not None
    assert found.attempts == 1
    assert found.last_error == "temporary error"
