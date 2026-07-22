from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.database.audit import AuditAction
from app.models.base import ConflictError, ValidationError
from app.modules.cnc.application.services.common import CncServiceBase, decimal
from app.modules.cnc.domain.entities import CncMaterialTransactionType
from app.modules.cnc.infrastructure.models import CncMaterialTransactionModel
from app.modules.cnc.infrastructure.repositories import (
    CncMaterialTransactionRepository,
    CncWorkOrderRepository,
)
from app.modules.inventory.domain.entities import InventoryDocumentType


class CncMaterialService(CncServiceBase):
    async def issue(
        self,
        work_order_id: UUID,
        data: dict[str, Any],
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> CncMaterialTransactionModel:
        return await self._post_material(
            work_order_id,
            data,
            transaction_type=CncMaterialTransactionType.ISSUE.value,
            document_type=InventoryDocumentType.ISSUE,
            actor_id=actor_id,
            user=user,
        )

    async def return_material(
        self,
        work_order_id: UUID,
        data: dict[str, Any],
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> CncMaterialTransactionModel:
        return await self._post_material(
            work_order_id,
            data,
            transaction_type=CncMaterialTransactionType.RETURN.value,
            document_type=InventoryDocumentType.RETURN_IN,
            actor_id=actor_id,
            user=user,
        )

    async def scrap(
        self,
        work_order_id: UUID,
        data: dict[str, Any],
        *,
        actor_id: UUID,
        user: Any | None = None,
    ) -> CncMaterialTransactionModel:
        return await self._post_material(
            work_order_id,
            data,
            transaction_type=CncMaterialTransactionType.SCRAP.value,
            document_type=InventoryDocumentType.ADJUSTMENT_OUT,
            actor_id=actor_id,
            user=user,
        )

    async def _post_material(
        self,
        work_order_id: UUID,
        data: dict[str, Any],
        *,
        transaction_type: str,
        document_type: InventoryDocumentType,
        actor_id: UUID,
        user: Any | None,
    ) -> CncMaterialTransactionModel:
        try:
            work_order = await self.get_work_order(work_order_id)
            await self.ensure_work_order_scope(work_order, user)
            await self.ensure_work_order_editable(work_order)
            if work_order.material_item_id is None:
                raise ValidationError("CNC work order has no stock material.")
            quantity = decimal(data["quantity"])
            if quantity <= 0:
                raise ValidationError("Quantity must be greater than zero.")
            if transaction_type == CncMaterialTransactionType.ISSUE.value:
                planned_remaining = (
                    work_order.planned_material_quantity - work_order.issued_material_quantity
                )
                if quantity > planned_remaining and not data.get("allow_overissue"):
                    raise ConflictError(
                        "Cannot issue above planned material quantity without permission."
                    )
            if transaction_type in {
                CncMaterialTransactionType.RETURN.value,
                CncMaterialTransactionType.SCRAP.value,
            }:
                available = (
                    work_order.issued_material_quantity
                    - work_order.returned_material_quantity
                    - work_order.scrapped_material_quantity
                )
                if quantity > available:
                    raise ConflictError("Cannot return or scrap more material than issued.")
            document_id = await self.inventory_document(
                organization_id=work_order.organization_id,
                document_type=document_type,
                source_warehouse_id=(
                    work_order.source_warehouse_id
                    if document_type
                    in {InventoryDocumentType.ISSUE, InventoryDocumentType.ADJUSTMENT_OUT}
                    else None
                ),
                destination_warehouse_id=(
                    work_order.source_warehouse_id
                    if document_type == InventoryDocumentType.RETURN_IN
                    else None
                ),
                item_id=work_order.material_item_id,
                quantity=quantity,
                actor_id=actor_id,
                user=user,
                location_id=data.get("location_id"),
                reference=work_order.work_order_number,
                notes=data.get("notes"),
            )
            transaction = await CncMaterialTransactionRepository(self.session).create(
                CncMaterialTransactionModel(
                    work_order_id=work_order.id,
                    transaction_type=transaction_type,
                    inventory_document_id=document_id,
                    material_item_id=work_order.material_item_id,
                    warehouse_id=work_order.source_warehouse_id,
                    location_id=data.get("location_id"),
                    lot_id=data.get("lot_id"),
                    quantity=quantity,
                    reason=data.get("reason"),
                    created_by_user_id=actor_id,
                    posted_at=datetime.now(UTC),
                )
            )
            if transaction_type == CncMaterialTransactionType.ISSUE.value:
                work_order.issued_material_quantity += quantity
            elif transaction_type == CncMaterialTransactionType.RETURN.value:
                work_order.returned_material_quantity += quantity
            elif transaction_type == CncMaterialTransactionType.SCRAP.value:
                work_order.scrapped_material_quantity += quantity
            await CncWorkOrderRepository(self.session).update(work_order)
            await self.audit(
                action=AuditAction.UPDATE.value,
                entity_type="cnc_material_transaction",
                entity_id=transaction.id,
                actor_id=actor_id,
                after={"type": transaction_type, "quantity": str(quantity)},
            )
            await self.unit_of_work.commit()
            await self.unit_of_work.refresh(transaction)
            return transaction
        except Exception:
            await self.unit_of_work.rollback()
            raise
