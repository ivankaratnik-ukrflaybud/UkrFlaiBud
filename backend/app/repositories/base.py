from typing import Protocol, TypeVar
from uuid import UUID

EntityT = TypeVar("EntityT")


class Repository(Protocol[EntityT]):
    async def create(self, entity: EntityT) -> EntityT:
        raise NotImplementedError

    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> EntityT | None:
        raise NotImplementedError

    async def update(self, entity: EntityT) -> EntityT:
        raise NotImplementedError

    async def soft_delete(self, entity_id: UUID, *, actor_id: UUID | None = None) -> None:
        raise NotImplementedError

    async def list(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[EntityT]:
        raise NotImplementedError
