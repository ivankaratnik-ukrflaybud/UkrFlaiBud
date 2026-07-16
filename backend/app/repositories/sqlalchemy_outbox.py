from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.outbox import OutboxEvent
from app.repositories.sqlalchemy import SQLAlchemyRepository


class SQLAlchemyOutboxRepository(SQLAlchemyRepository[OutboxEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OutboxEvent)

    async def list_pending(self, *, limit: int = 100) -> list[OutboxEvent]:
        statement = (
            select(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .order_by(OutboxEvent.occurred_at.asc(), OutboxEvent.created_at.asc())
            .limit(limit)
        )
        result = await self.session.scalars(statement)
        return list(result.all())

    async def mark_processed(self, event_id: UUID, *, processed_at: datetime | None = None) -> None:
        event = await self.get(event_id)
        if event is None:
            return

        event.processed_at = processed_at or datetime.now(UTC)
        event.last_error = None
        await self.session.flush()

    async def mark_failed(self, event_id: UUID, error: str) -> None:
        event = await self.get(event_id)
        if event is None:
            return

        event.attempts += 1
        event.last_error = error
        await self.session.flush()
