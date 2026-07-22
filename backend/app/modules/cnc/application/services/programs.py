from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates
from app.modules.cnc.domain.entities import CncProgramStatus
from app.modules.cnc.infrastructure.models import CncProgramModel
from app.modules.cnc.infrastructure.repositories import CncProgramRepository
from app.schemas.pagination import PageRequest, SortDirection

APPROVED_LOCKED_FIELDS = {
    "code",
    "revision",
    "file_type",
    "storage_key",
    "checksum",
    "source_file_name",
    "machine_type",
    "compatible_machine_ids",
}


class CncProgramService(CncServiceBase):
    async def create(self, data: dict[str, Any], *, actor_id: UUID) -> CncProgramModel:
        await self.ensure_organization(data["organization_id"])
        if await CncProgramRepository(self.session).exists_revision(
            data["organization_id"], data["code"], data["revision"]
        ):
            raise ConflictError("CNC program revision must be unique.", {"field": "revision"})
        program = await CncProgramRepository(self.session).create(
            CncProgramModel(**data, created_by_user_id=actor_id)
        )
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_program",
            entity_id=program.id,
            actor_id=actor_id,
            after={"code": program.code, "revision": program.revision},
        )
        await self.commit_refresh(program)
        return program

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[CncProgramModel], int]:
        return await CncProgramRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, program_id: UUID) -> CncProgramModel:
        return await self.get_program(program_id)

    async def update(
        self,
        program_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> CncProgramModel:
        program = await self.get(program_id)
        if expected_version is not None and program.version != expected_version:
            raise ConflictError("Entity version conflict.")
        if (
            program.program_status == CncProgramStatus.APPROVED.value
            and APPROVED_LOCKED_FIELDS & data.keys()
        ):
            raise ConflictError("Approved CNC program revision is immutable.")
        next_code = data.get("code", program.code)
        next_revision = data.get("revision", program.revision)
        if await CncProgramRepository(self.session).exists_revision(
            program.organization_id, next_code, next_revision, exclude_id=program.id
        ):
            raise ConflictError("CNC program revision must be unique.", {"field": "revision"})
        apply_updates(program, data)
        await CncProgramRepository(self.session).update(program)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_program",
            entity_id=program.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(program)
        return program

    async def approve(self, program_id: UUID, *, actor_id: UUID) -> CncProgramModel:
        program = await self.get(program_id)
        if not program.storage_key and not program.source_file_name:
            raise ValidationError("Program file metadata is required before approval.")
        if program.program_status == CncProgramStatus.OBSOLETE.value:
            raise ConflictError("Obsolete CNC program cannot be approved.")
        program.program_status = CncProgramStatus.APPROVED.value
        program.approved_by_user_id = actor_id
        program.approved_at = datetime.now(UTC)
        await CncProgramRepository(self.session).update(program)
        await self.audit(
            action="approve",
            entity_type="cnc_program",
            entity_id=program.id,
            actor_id=actor_id,
            after={"status": program.program_status},
        )
        await self.commit_refresh(program)
        return program

    async def obsolete(self, program_id: UUID, *, actor_id: UUID) -> CncProgramModel:
        program = await self.get(program_id)
        program.program_status = CncProgramStatus.OBSOLETE.value
        await CncProgramRepository(self.session).update(program)
        await self.audit(
            action="obsolete",
            entity_type="cnc_program",
            entity_id=program.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(program)
        return program
