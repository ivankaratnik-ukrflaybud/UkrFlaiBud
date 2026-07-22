from __future__ import annotations

from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates
from app.modules.cnc.infrastructure.models import CncToolModel
from app.modules.cnc.infrastructure.repositories import CncToolRepository
from app.schemas.pagination import PageRequest, SortDirection


class CncToolService(CncServiceBase):
    async def create(self, data: dict[str, Any], *, actor_id: UUID) -> CncToolModel:
        await self.ensure_organization(data["organization_id"])
        await self.ensure_item(data["organization_id"], data.get("inventory_item_id"))
        repository = CncToolRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError("CNC tool code must be unique.", {"field": "code"})
        tool = await repository.create(CncToolModel(**data))
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_tool",
            entity_id=tool.id,
            actor_id=actor_id,
            after={"code": tool.code},
        )
        await self.commit_refresh(tool)
        return tool

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[CncToolModel], int]:
        return await CncToolRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self, tool_id: UUID, data: dict[str, Any], *, expected_version: int | None, actor_id: UUID
    ) -> CncToolModel:
        tool = await CncToolRepository(self.session).get(tool_id)
        if tool is None:
            from app.models.base import EntityNotFoundError

            raise EntityNotFoundError("CNC tool not found.", {"id": str(tool_id)})
        if expected_version is not None and tool.version != expected_version:
            raise ConflictError("Entity version conflict.")
        if "code" in data and await CncToolRepository(self.session).exists_by_code(
            tool.organization_id, data["code"], exclude_id=tool.id
        ):
            raise ConflictError("CNC tool code must be unique.", {"field": "code"})
        apply_updates(tool, data)
        await CncToolRepository(self.session).update(tool)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_tool",
            entity_id=tool.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(tool)
        return tool

    async def soft_delete(self, tool_id: UUID, *, actor_id: UUID) -> None:
        await CncToolRepository(self.session).soft_delete(tool_id)
        await self.audit(
            action=AuditAction.DELETE.value,
            entity_type="cnc_tool",
            entity_id=tool_id,
            actor_id=actor_id,
        )
        await self.unit_of_work.commit()
