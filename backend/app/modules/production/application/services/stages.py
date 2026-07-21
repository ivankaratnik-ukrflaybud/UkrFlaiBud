from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.production.application.services.common import ProductionServiceBase
from app.modules.production.domain.entities import ProductionOrderStatus, ProductionStageStatus
from app.modules.production.infrastructure.models import (
    ProductionOrderStageModel,
    ProductionStageTemplateModel,
)
from app.modules.production.infrastructure.repositories import (
    ProductionOrderRepository,
    ProductionStageRepository,
    ProductionStageTemplateRepository,
)
from app.schemas.pagination import PageRequest, SortDirection

STAGE_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"ready", "in_progress", "blocked", "skipped", "cancelled"},
    "ready": {"in_progress", "blocked", "skipped", "cancelled"},
    "in_progress": {"blocked", "completed", "cancelled"},
    "blocked": {"ready", "in_progress", "cancelled"},
}


class StageService(ProductionServiceBase):
    async def create_template(
        self, data: dict[str, Any], *, actor_id: UUID
    ) -> ProductionStageTemplateModel:
        await self.ensure_department(data["organization_id"], data.get("default_department_id"))
        template = await ProductionStageTemplateRepository(self.session).create(
            ProductionStageTemplateModel(**data)
        )
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="production_stage_template",
            entity_id=template.id,
            actor_id=actor_id,
            after={"code": template.code, "name": template.name},
        )
        await self.commit_refresh(template)
        return template

    async def list_templates(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[ProductionStageTemplateModel], int]:
        return await ProductionStageTemplateRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def add_stage(
        self, order_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> ProductionOrderStageModel:
        order = await self.get_order(order_id)
        await self.ensure_order_editable(order)
        template = None
        if data.get("stage_template_id"):
            template = await ProductionStageTemplateRepository(self.session).get(
                data["stage_template_id"]
            )
            if template is None:
                raise ValidationError("Stage template not found.")
        stage = await ProductionStageRepository(self.session).create(
            ProductionOrderStageModel(
                production_order_id=order_id,
                stage_template_id=data.get("stage_template_id"),
                sequence=data["sequence"],
                code_snapshot=template.code if template else data.get("code_snapshot"),
                name=data.get("name") or (template.name if template else None),
                description=data.get("description") or (template.description if template else None),
                status=data.get("status", ProductionStageStatus.PENDING.value),
                department_id=data.get("department_id")
                or (template.default_department_id if template else None),
                workplace_id=data.get("workplace_id"),
                responsible_employee_id=data.get("responsible_employee_id"),
                planned_start_at=data.get("planned_start_at"),
                planned_end_at=data.get("planned_end_at"),
            )
        )
        if not stage.name:
            raise ValidationError("Stage name is required.")
        await self.audit(
            action=AuditAction.CREATE.value,
            entity_type="production_order_stage",
            entity_id=stage.id,
            actor_id=actor_id,
            after={"name": stage.name, "sequence": stage.sequence},
        )
        await self.commit_refresh(stage)
        return stage

    async def list_order_stages(self, order_id: UUID) -> list[ProductionOrderStageModel]:
        await self.get_order(order_id)
        return await ProductionStageRepository(self.session).list_for_order(order_id)

    async def transition_stage(
        self,
        order_id: UUID,
        stage_id: UUID,
        target_status: str,
        *,
        actor_id: UUID,
        reason: str | None = None,
        notes: str | None = None,
    ) -> ProductionOrderStageModel:
        order = await self.get_order(order_id)
        await self.ensure_order_editable(order)
        stage = await ProductionStageRepository(self.session).get(stage_id)
        if stage is None or stage.production_order_id != order_id:
            raise ValidationError("Production stage not found.")
        if target_status not in STAGE_TRANSITIONS.get(stage.status, set()):
            raise ConflictError("Invalid production stage status transition.")
        if target_status == ProductionStageStatus.BLOCKED.value and not reason:
            raise ValidationError("Blocked stage reason is required.")
        before = {"status": stage.status, "progress_percent": stage.progress_percent}
        stage.status = target_status
        now = datetime.now(UTC)
        if target_status == ProductionStageStatus.IN_PROGRESS.value:
            stage.actual_start_at = stage.actual_start_at or now
            if order.status in {
                ProductionOrderStatus.RELEASED.value,
                ProductionOrderStatus.MATERIALS_RESERVED.value,
            }:
                order.status = ProductionOrderStatus.IN_PROGRESS.value
                order.actual_start_date = order.actual_start_date or now
                await ProductionOrderRepository(self.session).update(order)
        if target_status == ProductionStageStatus.COMPLETED.value:
            stage.progress_percent = 100
            stage.actual_end_at = now
            stage.completion_notes = notes
            await self.outbox(
                "production.stage.completed",
                "production_order_stage",
                stage.id,
                {"production_order_id": str(order.id), "stage": stage.name},
            )
        if target_status == ProductionStageStatus.BLOCKED.value:
            stage.blocked_reason = reason
        await ProductionStageRepository(self.session).update(stage)
        await self.audit(
            action=AuditAction.UPDATE.value,
            entity_type="production_order_stage",
            entity_id=stage.id,
            actor_id=actor_id,
            before=before,
            after={"status": stage.status, "progress_percent": stage.progress_percent},
        )
        await self.commit_refresh(stage)
        return stage
