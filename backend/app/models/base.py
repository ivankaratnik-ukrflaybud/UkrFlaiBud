from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class DomainModel:
    id: UUID
    created_at: datetime
    updated_at: datetime

