from __future__ import annotations

from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates
from app.modules.cnc.infrastructure.models import CncPartModel
from app.modules.cnc.infrastructure.repositories import CncPartRepository
from app.schemas.pagination import PageRequest, SortDirection


class CncPartService(CncServiceBase):
    async def create(self, data: dict[str, Any], *, actor_id: UUID) -> CncPartModel:
        await self.ensure_organization(data["organization_id"])
        await self.ensure_item(data["organization_id"], data.get("inventory_item_id"))
        material = await self.ensure_item(data["organization_id"], data.get("material_item_id"))
        if material and not data.get("material_name_snapshot"):
            data["material_name_snapshot"] = material.name
        if await CncPartRepository(self.session).exists_by_code(
            data["organization_id"], data["code"]
        ):
            raise ConflictError("CNC part code must be unique.", {"field": "code"})
        part = await CncPartRepository(self.session).create(CncPartModel(**data))
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_part",
            entity_id=part.id,
            actor_id=actor_id,
            after={"code": part.code, "name": part.name},
        )
        await self.commit_refresh(part)
        return part

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[CncPartModel], int]:
        return await CncPartRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, part_id: UUID) -> CncPartModel:
        return await self.get_part(part_id)

    async def update(
        self, part_id: UUID, data: dict[str, Any], *, expected_version: int | None, actor_id: UUID
    ) -> CncPartModel:
        part = await self.get(part_id)
        if expected_version is not None and part.version != expected_version:
            raise ConflictError("Entity version conflict.")
        if "code" in data and await CncPartRepository(self.session).exists_by_code(
            part.organization_id, data["code"], exclude_id=part.id
        ):
            raise ConflictError("CNC part code must be unique.", {"field": "code"})
        material = await self.ensure_item(part.organization_id, data.get("material_item_id"))
        if material and not data.get("material_name_snapshot"):
            data["material_name_snapshot"] = material.name
        apply_updates(part, data)
        await CncPartRepository(self.session).update(part)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_part",
            entity_id=part.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(part)
        return part

    async def soft_delete(self, part_id: UUID, *, actor_id: UUID) -> None:
        await CncPartRepository(self.session).soft_delete(part_id)
        await self.audit(
            action=AuditAction.DELETE.value,
            entity_type="cnc_part",
            entity_id=part_id,
            actor_id=actor_id,
        )
        await self.unit_of_work.commit()
