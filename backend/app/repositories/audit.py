from typing import Protocol

from app.database.audit import AuditLog


class AuditLogRepository(Protocol):
    async def create(self, audit_log: AuditLog) -> AuditLog:
        raise NotImplementedError
