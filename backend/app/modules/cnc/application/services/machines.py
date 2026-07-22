from __future__ import annotations

from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates
from app.modules.cnc.domain.entities import CncMachineStatus
from app.modules.cnc.infrastructure.models import CncMachineModel
from app.modules.cnc.infrastructure.repositories import CncMachineRepository
from app.schemas.pagination import PageRequest, SortDirection

ALLOWED_MACHINE_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "available": {"setup", "maintenance", "fault", "unavailable", "decommissioned"},
    "setup": {"available", "running", "paused", "fault", "maintenance"},
    "running": {"paused", "available", "fault"},
    "paused": {"running", "available", "fault", "maintenance"},
    "maintenance": {"available", "unavailable", "decommissioned"},
    "fault": {"maintenance", "available", "unavailable"},
    "unavailable": {"available", "maintenance", "decommissioned"},
    "decommissioned": set(),
}


class CncMachineService(CncServiceBase):
    async def create(
        self, data: dict[str, Any], *, actor_id: UUID, user: Any | None = None
    ) -> CncMachineModel:
        await self.ensure_organization(data["organization_id"])
        await self.ensure_site(data["organization_id"], data["site_id"])
        await self.ensure_site_access(user, data["site_id"])
        await self.ensure_department(data["organization_id"], data.get("department_id"))
        await self.ensure_employee(
            data["organization_id"], data.get("current_operator_employee_id")
        )
        repository = CncMachineRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError("CNC machine code must be unique.", {"field": "code"})
        machine = await repository.create(CncMachineModel(**data))
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_machine",
            entity_id=machine.id,
            actor_id=actor_id,
            after={"code": machine.code, "status": machine.status},
        )
        await self.commit_refresh(machine)
        return machine

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: Any | None = None,
    ) -> tuple[list[CncMachineModel], int]:
        if user and not getattr(user, "is_superuser", False):
            from app.modules.inventory.application.services import InventoryScopeService

            site_ids = await InventoryScopeService(self.unit_of_work).accessible_site_ids(user)
            if not site_ids:
                return [], 0
            filters = {**filters, "site_ids": site_ids}
        return await CncMachineRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, machine_id: UUID, *, user: Any | None = None) -> CncMachineModel:
        machine = await self.get_machine(machine_id)
        await self.ensure_site_access(user, machine.site_id)
        return machine

    async def update(
        self,
        machine_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
        user: Any | None = None,
    ) -> CncMachineModel:
        machine = await self.get(machine_id, user=user)
        if expected_version is not None and machine.version != expected_version:
            raise ConflictError("Entity version conflict.")
        if "code" in data and await CncMachineRepository(self.session).exists_by_code(
            machine.organization_id, data["code"], exclude_id=machine.id
        ):
            raise ConflictError("CNC machine code must be unique.", {"field": "code"})
        if "site_id" in data:
            await self.ensure_site(machine.organization_id, data["site_id"])
            await self.ensure_site_access(user, data["site_id"])
        await self.ensure_department(machine.organization_id, data.get("department_id"))
        await self.ensure_employee(
            machine.organization_id, data.get("current_operator_employee_id")
        )
        before = {"status": machine.status, "code": machine.code}
        apply_updates(machine, data)
        await CncMachineRepository(self.session).update(machine)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_machine",
            entity_id=machine.id,
            actor_id=actor_id,
            before=before,
            after={"status": machine.status, "code": machine.code},
        )
        await self.commit_refresh(machine)
        return machine

    async def set_status(
        self,
        machine_id: UUID,
        status: str,
        *,
        actor_id: UUID,
        user: Any | None = None,
        reason: str | None = None,
    ) -> CncMachineModel:
        machine = await self.get(machine_id, user=user)
        if status not in ALLOWED_MACHINE_STATUS_TRANSITIONS.get(machine.status, set()):
            raise ConflictError("Invalid CNC machine status transition.")
        if status == CncMachineStatus.RUNNING.value:
            running = await CncMachineRepository(self.session).exists(
                CncMachineModel.id == machine.id,
                CncMachineModel.status == CncMachineStatus.RUNNING.value,
            )
            if running:
                raise ConflictError("Machine is already running.")
        before = {"status": machine.status}
        machine.status = status
        if status == CncMachineStatus.DECOMMISSIONED.value:
            machine.is_active = False
        await CncMachineRepository(self.session).update(machine)
        await self.audit(
            action="status",
            entity_type="cnc_machine",
            entity_id=machine.id,
            actor_id=actor_id,
            before=before,
            after={"status": status, "reason": reason},
        )
        if status == CncMachineStatus.FAULT.value:
            await self.outbox(
                "cnc.machine.fault", "cnc_machine", machine.id, {"code": machine.code}
            )
        await self.commit_refresh(machine)
        return machine

    async def soft_delete(
        self, machine_id: UUID, *, actor_id: UUID, user: Any | None = None
    ) -> None:
        machine = await self.get(machine_id, user=user)
        if machine.status in {CncMachineStatus.SETUP.value, CncMachineStatus.RUNNING.value}:
            raise ConflictError("Active machine cannot be deleted.")
        await CncMachineRepository(self.session).soft_delete(machine.id)
        await self.audit(
            action=AuditAction.DELETE.value,
            entity_type="cnc_machine",
            entity_id=machine.id,
            actor_id=actor_id,
        )
        await self.unit_of_work.commit()
