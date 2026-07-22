from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from app.modules.cnc.application.services.common import CncServiceBase
from app.modules.cnc.domain.entities import CncMachineStatus, CncProgramStatus
from app.modules.cnc.infrastructure.models import (
    CncMachineModel,
    CncWorkOrderModel,
)
from app.modules.cnc.infrastructure.repositories import (
    CncExecutionLogRepository,
    CncWorkOrderOutputRepository,
)


class CncQueryService(CncServiceBase):
    async def dashboard(self, organization_id: UUID, *, user: Any | None = None) -> dict[str, Any]:
        filters: list[Any] = [CncWorkOrderModel.organization_id == organization_id]
        if user and not getattr(user, "is_superuser", False):
            from app.modules.inventory.application.services import InventoryScopeService

            site_ids = await InventoryScopeService(self.unit_of_work).accessible_site_ids(user)
            if not site_ids:
                return _empty_dashboard()
            filters.append(CncWorkOrderModel.site_id.in_(site_ids))
        today = datetime.now(UTC).date()
        scalar = self.session.scalar
        return {
            "running_machines": await scalar(
                select(func.count())
                .select_from(CncMachineModel)
                .where(
                    CncMachineModel.organization_id == organization_id,
                    CncMachineModel.status == CncMachineStatus.RUNNING.value,
                )
            )
            or 0,
            "available_machines": await scalar(
                select(func.count())
                .select_from(CncMachineModel)
                .where(
                    CncMachineModel.organization_id == organization_id,
                    CncMachineModel.status == CncMachineStatus.AVAILABLE.value,
                    CncMachineModel.is_active.is_(True),
                )
            )
            or 0,
            "queued_work_orders": await scalar(
                select(func.count())
                .select_from(CncWorkOrderModel)
                .where(*filters, CncWorkOrderModel.status == "queued")
            )
            or 0,
            "running_work_orders": await scalar(
                select(func.count())
                .select_from(CncWorkOrderModel)
                .where(*filters, CncWorkOrderModel.status == "running")
            )
            or 0,
            "blocked_work_orders": await scalar(
                select(func.count())
                .select_from(CncWorkOrderModel)
                .where(*filters, CncWorkOrderModel.status == "blocked")
            )
            or 0,
            "overdue_work_orders": await scalar(
                select(func.count())
                .select_from(CncWorkOrderModel)
                .where(
                    *filters,
                    CncWorkOrderModel.planned_end_at < datetime.now(UTC),
                    CncWorkOrderModel.status.notin_(["completed", "cancelled"]),
                )
            )
            or 0,
            "completed_today": await scalar(
                select(func.count())
                .select_from(CncWorkOrderModel)
                .where(
                    *filters,
                    func.date(CncWorkOrderModel.actual_end_at) == today,
                    CncWorkOrderModel.status == "completed",
                )
            )
            or 0,
            "rejected_today": await scalar(
                select(func.coalesce(func.sum(CncWorkOrderModel.rejected_quantity), 0)).where(
                    *filters,
                    func.date(CncWorkOrderModel.updated_at) == today,
                )
            )
            or 0,
        }

    async def readiness(self, work_order_id: UUID) -> dict[str, Any]:
        work_order = await self.get_work_order(work_order_id)
        machine = await self.get_machine(work_order.machine_id) if work_order.machine_id else None
        program = await self.get_program(work_order.program_id) if work_order.program_id else None
        checklist = [
            {
                "code": "machine",
                "label": "Верстат готовий",
                "ready": bool(
                    machine
                    and machine.is_active
                    and machine.status
                    not in {"fault", "maintenance", "unavailable", "decommissioned"}
                ),
            },
            {
                "code": "program",
                "label": "Програма готова",
                "ready": bool(
                    program and program.program_status == CncProgramStatus.APPROVED.value
                ),
            },
            {
                "code": "material",
                "label": "Матеріал видано",
                "ready": not work_order.material_item_id or work_order.issued_material_quantity > 0,
            },
            {"code": "tooling", "label": "Інструмент підготовлено", "ready": True},
            {
                "code": "operator",
                "label": "Оператор призначений",
                "ready": bool(work_order.operator_employee_id),
            },
        ]
        return {
            "work_order_id": work_order.id,
            "ready": all(item["ready"] for item in checklist),
            "checklist": checklist,
        }

    async def history(self, work_order_id: UUID):
        return await CncExecutionLogRepository(self.session).list_for_work_order(work_order_id)

    async def outputs(self, work_order_id: UUID):
        return await CncWorkOrderOutputRepository(self.session).list_for_work_order(work_order_id)


def _empty_dashboard() -> dict[str, Any]:
    return {
        "running_machines": 0,
        "available_machines": 0,
        "queued_work_orders": 0,
        "running_work_orders": 0,
        "blocked_work_orders": 0,
        "overdue_work_orders": 0,
        "completed_today": 0,
        "rejected_today": 0,
    }
