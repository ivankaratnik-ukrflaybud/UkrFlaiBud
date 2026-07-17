# ruff: noqa: F401,I001
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditAction, AuditLog
from app.database.outbox import OutboxEvent
from app.models.base import (
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.identity.application.services import UserService
from app.modules.identity.infrastructure.models import UserModel
from app.modules.inventory.domain.entities import (
    InventoryDocumentStatus,
    InventoryDocumentType,
    InventoryMovementKind,
    ItemType,
    SerialStatus,
)
from app.modules.inventory.infrastructure.models import (
    InventoryDocumentLineModel,
    InventoryDocumentLineSerialModel,
    InventoryDocumentModel,
    InventoryLotModel,
    InventoryMovementModel,
    InventorySerialModel,
    ItemCategoryModel,
    ItemModel,
    SiteModel,
    StockBalanceModel,
    StorageLocationModel,
    UnitOfMeasureModel,
    WarehouseModel,
)
from app.modules.inventory.infrastructure.repositories import (
    CategoryRepository,
    DocumentLineRepository,
    DocumentRepository,
    InventoryScopeRepository,
    ItemRepository,
    LotRepository,
    MovementRepository,
    SerialRepository,
    SiteRepository,
    StockBalanceRepository,
    StorageLocationRepository,
    UnitRepository,
    WarehouseRepository,
)
from app.modules.organizations.infrastructure.models import EmployeeModel, OrganizationModel
from app.repositories.sqlalchemy_audit import SQLAlchemyAuditLogRepository
from app.repositories.sqlalchemy_outbox import SQLAlchemyOutboxRepository
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection

STOCK_IN_TYPES = {
    InventoryDocumentType.RECEIPT,
    InventoryDocumentType.ADJUSTMENT_IN,
    InventoryDocumentType.RETURN_IN,
}
STOCK_OUT_TYPES = {
    InventoryDocumentType.ISSUE,
    InventoryDocumentType.ADJUSTMENT_OUT,
    InventoryDocumentType.RETURN_OUT,
}


class InventoryService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def _commit(self) -> None:
        await self.unit_of_work.commit()

    @staticmethod
    def _ensure_version(entity: Any, expected_version: int | None) -> None:
        if expected_version is not None and entity.version != expected_version:
            raise ConflictError(
                "Entity version conflict.",
                {"expected_version": expected_version, "current_version": entity.version},
            )

    async def _ensure_organization(self, organization_id: UUID) -> None:
        exists = await self.session.scalar(
            select(func.count())
            .select_from(OrganizationModel)
            .where(OrganizationModel.id == organization_id)
        )
        if not exists:
            raise EntityNotFoundError("Organization not found.", {"id": str(organization_id)})

    async def _ensure_employee(self, organization_id: UUID, employee_id: UUID | None) -> None:
        if employee_id is None:
            return
        employee = await self.session.get(EmployeeModel, employee_id)
        if employee is None or employee.deleted_at is not None:
            raise EntityNotFoundError("Employee not found.", {"id": str(employee_id)})
        if employee.organization_id != organization_id:
            raise ValidationError("Employee must belong to the same organization.")

    async def _audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor_id: UUID | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await SQLAlchemyAuditLogRepository(self.session).create(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                before_data=before,
                after_data=after,
                correlation_id=None,
            )
        )

    async def _outbox(
        self, event_type: str, aggregate_type: str, aggregate_id: UUID, payload: dict[str, Any]
    ) -> None:
        await SQLAlchemyOutboxRepository(self.session).create(
            OutboxEvent(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                payload=payload,
                occurred_at=datetime.now(UTC),
            )
        )


def _apply_updates(entity: Any, data: dict[str, Any]) -> None:
    for field, value in data.items():
        setattr(entity, field, value)


__all__ = [
    "Any",
    "UTC",
    "datetime",
    "Decimal",
    "UUID",
    "delete",
    "func",
    "or_",
    "select",
    "AsyncSession",
    "AuditAction",
    "AuditLog",
    "OutboxEvent",
    "ConflictError",
    "EntityNotFoundError",
    "PermissionDeniedError",
    "ValidationError",
    "UserService",
    "UserModel",
    "InventoryDocumentStatus",
    "InventoryDocumentType",
    "InventoryMovementKind",
    "ItemType",
    "SerialStatus",
    "InventoryDocumentLineModel",
    "InventoryDocumentLineSerialModel",
    "InventoryDocumentModel",
    "InventoryLotModel",
    "InventoryMovementModel",
    "InventorySerialModel",
    "ItemCategoryModel",
    "ItemModel",
    "SiteModel",
    "StockBalanceModel",
    "StorageLocationModel",
    "UnitOfMeasureModel",
    "WarehouseModel",
    "CategoryRepository",
    "DocumentLineRepository",
    "DocumentRepository",
    "InventoryScopeRepository",
    "ItemRepository",
    "LotRepository",
    "MovementRepository",
    "SerialRepository",
    "SiteRepository",
    "StockBalanceRepository",
    "StorageLocationRepository",
    "UnitRepository",
    "WarehouseRepository",
    "EmployeeModel",
    "OrganizationModel",
    "SQLAlchemyAuditLogRepository",
    "SQLAlchemyOutboxRepository",
    "SQLAlchemyUnitOfWork",
    "PageRequest",
    "SortDirection",
    "STOCK_IN_TYPES",
    "STOCK_OUT_TYPES",
    "InventoryService",
    "_apply_updates",
]
