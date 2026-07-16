from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.database.outbox import OutboxEvent


class OutboxRepository(Protocol):
    async def create(self, event: OutboxEvent) -> OutboxEvent:
        raise NotImplementedError

    async def list_pending(self, *, limit: int = 100) -> list[OutboxEvent]:
        raise NotImplementedError

    async def mark_processed(self, event_id: UUID, *, processed_at: datetime | None = None) -> None:
        raise NotImplementedError

    async def mark_failed(self, event_id: UUID, error: str) -> None:
        raise NotImplementedError
