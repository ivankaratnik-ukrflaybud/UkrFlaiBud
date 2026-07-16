from typing import Protocol, TypeVar
from uuid import UUID

from app.schemas.pagination import SortDirection

EntityT = TypeVar("EntityT")


class ListRepository(Protocol[EntityT]):
    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> EntityT | None:
        raise NotImplementedError

    async def list(
        self,
        *,
        filters: dict[str, object],
        sort_by: str,
        sort_direction: SortDirection,
        limit: int,
        offset: int,
        include_deleted: bool = False,
    ) -> tuple[list[EntityT], int]:
        raise NotImplementedError


class OrganizationRepository(ListRepository[EntityT], Protocol):
    async def exists_by_edrpou(self, edrpou: str, *, exclude_id: UUID | None = None) -> bool:
        raise NotImplementedError


class CodedRepository(ListRepository[EntityT], Protocol):
    async def exists_by_code(
        self,
        organization_id: UUID,
        code: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        raise NotImplementedError


class EmployeeRepository(ListRepository[EntityT], Protocol):
    async def exists_by_personnel_number(
        self,
        organization_id: UUID,
        personnel_number: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        raise NotImplementedError
