from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select

from app.modules.production.application.services.common import ProductionServiceBase
from app.modules.production.infrastructure.models import ProductionOutputSerialModel


class SerialRegistrationService(ProductionServiceBase):
    async def list_for_order(self, order_id: UUID, *, user: Any | None = None) -> list[Any]:
        order = await self.get_order(order_id)
        await self.ensure_order_scope(order, user)
        result = await self.session.scalars(
            select(ProductionOutputSerialModel).where(
                ProductionOutputSerialModel.production_order_id == order_id
            )
        )
        return list(result.all())
