# ruff: noqa: F401,I001
from collections.abc import Sequence
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_unit_of_work
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.modules.inventory.application.services import (
    CatalogService,
    DocumentService,
    InventoryScopeService,
    LocationService,
    SiteService,
    StockService,
    TrackingService,
    WarehouseService,
)
from app.modules.inventory.domain.entities import (
    InventoryDocumentStatus,
    InventoryDocumentType,
    ItemType,
    SerialStatus,
)
from app.modules.inventory.presentation.schemas import (
    AttachSerialsPayload,
    CancelDocumentPayload,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    DocumentCreate,
    DocumentLineCreate,
    DocumentLineResponse,
    DocumentLineUpdate,
    DocumentResponse,
    DocumentUpdate,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    LocationCreate,
    LocationResponse,
    LocationUpdate,
    LotCreate,
    LotResponse,
    MovementResponse,
    SerialCreate,
    SerialResponse,
    SerialStatusUpdate,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    StockBalanceResponse,
    UnitCreate,
    UnitResponse,
    UnitUpdate,
    UserInventoryScopeResponse,
    UserInventoryScopeUpdate,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection


router = APIRouter(prefix="/inventory")
identity_scope_router = APIRouter(prefix="/identity")
UnitOfWorkDependency = Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)]
CurrentUserDependency = Annotated[UserModel, Depends(current_user)]
CurrentUserIdDependency = Annotated[UUID, Depends(current_user_id)]
SortDirectionQuery = Annotated[SortDirection, Query()]
SerialStatusQuery = Annotated[SerialStatus | None, Query(alias="status")]
DocumentStatusQuery = Annotated[InventoryDocumentStatus | None, Query(alias="status")]


def _page(
    items: Sequence[Any], total: int, page: int, page_size: int, schema: Any
) -> PaginatedResponse[Any]:
    return PaginatedResponse(
        items=[schema.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


__all__ = [
    "Sequence",
    "Annotated",
    "Any",
    "UUID",
    "APIRouter",
    "Depends",
    "Query",
    "Response",
    "status",
    "get_unit_of_work",
    "UserModel",
    "current_user",
    "current_user_id",
    "require_permission",
    "CatalogService",
    "DocumentService",
    "InventoryScopeService",
    "LocationService",
    "SiteService",
    "StockService",
    "TrackingService",
    "WarehouseService",
    "InventoryDocumentStatus",
    "InventoryDocumentType",
    "ItemType",
    "SerialStatus",
    "AttachSerialsPayload",
    "CancelDocumentPayload",
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    "DocumentCreate",
    "DocumentLineCreate",
    "DocumentLineResponse",
    "DocumentLineUpdate",
    "DocumentResponse",
    "DocumentUpdate",
    "ItemCreate",
    "ItemResponse",
    "ItemUpdate",
    "LocationCreate",
    "LocationResponse",
    "LocationUpdate",
    "LotCreate",
    "LotResponse",
    "MovementResponse",
    "SerialCreate",
    "SerialResponse",
    "SerialStatusUpdate",
    "SiteCreate",
    "SiteResponse",
    "SiteUpdate",
    "StockBalanceResponse",
    "UnitCreate",
    "UnitResponse",
    "UnitUpdate",
    "UserInventoryScopeResponse",
    "UserInventoryScopeUpdate",
    "WarehouseCreate",
    "WarehouseResponse",
    "WarehouseUpdate",
    "SQLAlchemyUnitOfWork",
    "PageRequest",
    "PaginatedResponse",
    "SortDirection",
    "router",
    "identity_scope_router",
    "UnitOfWorkDependency",
    "CurrentUserDependency",
    "CurrentUserIdDependency",
    "SortDirectionQuery",
    "SerialStatusQuery",
    "DocumentStatusQuery",
    "_page",
]
