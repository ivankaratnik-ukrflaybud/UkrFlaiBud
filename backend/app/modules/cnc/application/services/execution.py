from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.cnc.application.services.common import CncServiceBase
from app.modules.cnc.application.services.work_orders import CncWorkOrderService
from app.modules.cnc.domain.entities import CncWorkOrderStatus


class CncExecutionService(CncServiceBase):
    async def start_setup(self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id, CncWorkOrderStatus.SETUP.value, actor_id=actor_id, user=user
        )

    async def start(self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id, CncWorkOrderStatus.RUNNING.value, actor_id=actor_id, user=user
        )

    async def pause(
        self,
        work_order_id: UUID,
        *,
        actor_id: UUID,
        user: Any | None = None,
        reason: str | None = None,
    ):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id,
            CncWorkOrderStatus.PAUSED.value,
            actor_id=actor_id,
            user=user,
            reason=reason,
        )

    async def resume(self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id, CncWorkOrderStatus.RUNNING.value, actor_id=actor_id, user=user
        )

    async def block(
        self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None, reason: str | None
    ):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id,
            CncWorkOrderStatus.BLOCKED.value,
            actor_id=actor_id,
            user=user,
            reason=reason,
        )

    async def unblock(
        self, work_order_id: UUID, target_status: str, *, actor_id: UUID, user: Any | None = None
    ):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id, target_status, actor_id=actor_id, user=user
        )

    async def cancel(
        self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None, reason: str | None
    ):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id,
            CncWorkOrderStatus.CANCELLED.value,
            actor_id=actor_id,
            user=user,
            reason=reason,
        )

    async def complete(self, work_order_id: UUID, *, actor_id: UUID, user: Any | None = None):
        return await CncWorkOrderService(self.unit_of_work).transition(
            work_order_id, CncWorkOrderStatus.COMPLETED.value, actor_id=actor_id, user=user
        )
