from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditLog
from app.repositories.sqlalchemy import SQLAlchemyRepository


class SQLAlchemyAuditLogRepository(SQLAlchemyRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)
