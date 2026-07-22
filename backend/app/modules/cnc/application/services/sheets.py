from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, EntityNotFoundError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase, apply_updates, decimal
from app.modules.cnc.domain.entities import CncSheetPlanStatus
from app.modules.cnc.infrastructure.models import CncSheetPlanLineModel, CncSheetPlanModel
from app.modules.cnc.infrastructure.repositories import (
    CncSheetPlanLineRepository,
    CncSheetPlanRepository,
)
from app.schemas.pagination import PageRequest, SortDirection


class CncSheetPlanService(CncServiceBase):
    async def create(self, data: dict[str, Any], *, actor_id: UUID) -> CncSheetPlanModel:
        await self.ensure_organization(data["organization_id"])
        material = await self.ensure_item(data["organization_id"], data["material_item_id"])
        if material is not None:
            data["material_name_snapshot"] = data.get("material_name_snapshot") or material.name
        if decimal(data["planned_sheet_quantity"]) <= 0:
            raise ValidationError("Planned sheet quantity must be greater than zero.")
        repository = CncSheetPlanRepository(self.session)
        if await repository.exists_by_number(data["organization_id"], data["plan_number"]):
            raise ConflictError("CNC sheet plan number must be unique.", {"field": "plan_number"})
        plan = await repository.create(CncSheetPlanModel(**data, created_by_user_id=actor_id))
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
            after={"plan_number": plan.plan_number},
        )
        await self.commit_refresh(plan)
        return plan

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[CncSheetPlanModel], int]:
        return await CncSheetPlanRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get(self, sheet_plan_id: UUID) -> CncSheetPlanModel:
        return await self.get_sheet_plan(sheet_plan_id)

    async def update(
        self,
        sheet_plan_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> CncSheetPlanModel:
        plan = await self.get(sheet_plan_id)
        if plan.status != CncSheetPlanStatus.DRAFT.value:
            raise ConflictError("Approved CNC sheet plans are immutable; copy them to revise.")
        if expected_version is not None and plan.version != expected_version:
            raise ConflictError("Entity version conflict.")
        apply_updates(plan, data)
        await CncSheetPlanRepository(self.session).update(plan)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(plan)
        return plan

    async def add_line(
        self, sheet_plan_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> CncSheetPlanLineModel:
        plan = await self.get(sheet_plan_id)
        if plan.status != CncSheetPlanStatus.DRAFT.value:
            raise ConflictError("Approved CNC sheet plans are immutable; copy them to revise.")
        part = await self.get_part(data["cnc_part_id"])
        total = decimal(data["quantity_per_sheet"]) * decimal(plan.planned_sheet_quantity)
        line = await CncSheetPlanLineRepository(self.session).create(
            CncSheetPlanLineModel(
                sheet_plan_id=plan.id,
                cnc_part_id=part.id,
                part_code_snapshot=part.code,
                part_name_snapshot=part.name,
                drawing_revision_snapshot=part.drawing_revision,
                quantity_per_sheet=data["quantity_per_sheet"],
                total_planned_quantity=data.get("total_planned_quantity") or total,
                sort_order=data.get("sort_order", 10),
                notes=data.get("notes"),
            )
        )
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
            after={"line_added": str(line.id)},
        )
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(line)
        return line

    async def update_line(
        self,
        sheet_plan_id: UUID,
        line_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> CncSheetPlanLineModel:
        plan = await self.get(sheet_plan_id)
        if plan.status != CncSheetPlanStatus.DRAFT.value:
            raise ConflictError("Approved CNC sheet plans are immutable; copy them to revise.")
        line = await CncSheetPlanLineRepository(self.session).get(line_id)
        if line is None or line.sheet_plan_id != sheet_plan_id:
            raise EntityNotFoundError("CNC sheet plan line not found.", {"id": str(line_id)})
        if expected_version is not None and line.version != expected_version:
            raise ConflictError("Entity version conflict.")
        apply_updates(line, data)
        await CncSheetPlanLineRepository(self.session).update(line)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
            after={"line_updated": str(line.id)},
        )
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(line)
        return line

    async def delete_line(self, sheet_plan_id: UUID, line_id: UUID, *, actor_id: UUID) -> None:
        plan = await self.get(sheet_plan_id)
        if plan.status != CncSheetPlanStatus.DRAFT.value:
            raise ConflictError("Approved CNC sheet plans are immutable; copy them to revise.")
        line = await CncSheetPlanLineRepository(self.session).get(line_id)
        if line is None or line.sheet_plan_id != sheet_plan_id:
            raise EntityNotFoundError("CNC sheet plan line not found.", {"id": str(line_id)})
        await self.session.delete(line)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
            after={"line_deleted": str(line.id)},
        )
        await self.unit_of_work.commit()

    async def approve(self, sheet_plan_id: UUID, *, actor_id: UUID) -> CncSheetPlanModel:
        plan = await self.get(sheet_plan_id)
        if plan.status != CncSheetPlanStatus.DRAFT.value:
            raise ConflictError("Only draft CNC sheet plans can be approved.")
        lines = await CncSheetPlanLineRepository(self.session).list_for_plan(plan.id)
        if not lines:
            raise ValidationError("Sheet plan requires at least one line.")
        plan.status = CncSheetPlanStatus.APPROVED.value
        plan.approved_by_user_id = actor_id
        plan.approved_at = datetime.now(UTC)
        await CncSheetPlanRepository(self.session).update(plan)
        await self.audit(
            action="approve",
            entity_type="cnc_sheet_plan",
            entity_id=plan.id,
            actor_id=actor_id,
        )
        await self.commit_refresh(plan)
        return plan

    async def copy(
        self, sheet_plan_id: UUID, plan_number: str, *, actor_id: UUID
    ) -> CncSheetPlanModel:
        source = await self.get(sheet_plan_id)
        data = {
            "organization_id": source.organization_id,
            "plan_number": plan_number,
            "name": f"{source.name} copy",
            "material_item_id": source.material_item_id,
            "material_name_snapshot": source.material_name_snapshot,
            "sheet_length_mm": source.sheet_length_mm,
            "sheet_width_mm": source.sheet_width_mm,
            "thickness_mm": source.thickness_mm,
            "planned_sheet_quantity": source.planned_sheet_quantity,
            "estimated_utilization_percent": source.estimated_utilization_percent,
            "program_id": source.program_id,
            "machine_id": source.machine_id,
            "production_order_id": source.production_order_id,
            "notes": source.notes,
        }
        copy = await self.create(data, actor_id=actor_id)
        for line in await CncSheetPlanLineRepository(self.session).list_for_plan(source.id):
            await self.add_line(
                copy.id,
                {
                    "cnc_part_id": line.cnc_part_id,
                    "quantity_per_sheet": line.quantity_per_sheet,
                    "total_planned_quantity": line.total_planned_quantity,
                    "sort_order": line.sort_order,
                    "notes": line.notes,
                },
                actor_id=actor_id,
            )
        return copy
