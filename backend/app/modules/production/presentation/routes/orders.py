from __future__ import annotations

# ruff: noqa: B008
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel

from app.api.dependencies import get_unit_of_work
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.modules.production.application.services import (
    ProductionOrderService,
    ProductionQueryService,
)
from app.modules.production.presentation.schemas import (
    DashboardResponse,
    ProductionOrderCreate,
    ProductionOrderResponse,
    ProductionOrderUpdate,
    TransitionPayload,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


def _page(
    items: Sequence[object], total: int, page: int, page_size: int, model: type[BaseModel]
) -> PaginatedResponse[Any]:
    return PaginatedResponse[Any](
        items=[model.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("production.read"))],
)
async def dashboard(
    organization_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
) -> DashboardResponse:
    return DashboardResponse.model_validate(
        await ProductionQueryService(unit_of_work).dashboard(organization_id, user=user)
    )


@router.post(
    "/orders",
    response_model=ProductionOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("production.create"))],
)
async def create_order(
    payload: ProductionOrderCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> ProductionOrderResponse:
    return ProductionOrderResponse.model_validate(
        await ProductionOrderService(unit_of_work).create_order(
            payload.model_dump(exclude_unset=True), actor_id=user_id, user=user
        )
    )


@router.get(
    "/orders",
    response_model=PaginatedResponse[ProductionOrderResponse],
    dependencies=[Depends(require_permission("production.read"))],
)
async def list_orders(
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_direction: SortDirection = SortDirection.DESC,
    organization_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    site_id: UUID | None = None,
    department_id: UUID | None = None,
    product_item_id: UUID | None = None,
    responsible_employee_id: UUID | None = None,
    search: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[ProductionOrderResponse]:
    items, total = await ProductionOrderService(unit_of_work).list_orders(
        filters={
            "organization_id": organization_id,
            "status": status_filter,
            "priority": priority,
            "site_id": site_id,
            "department_id": department_id,
            "product_item_id": product_item_id,
            "responsible_employee_id": responsible_employee_id,
            "search": search,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, ProductionOrderResponse)


@router.get(
    "/orders/{order_id}",
    response_model=ProductionOrderResponse,
    dependencies=[Depends(require_permission("production.read"))],
)
async def get_order(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
) -> ProductionOrderResponse:
    return ProductionOrderResponse.model_validate(
        await ProductionOrderService(unit_of_work).get(order_id, user=user)
    )


@router.patch(
    "/orders/{order_id}",
    response_model=ProductionOrderResponse,
    dependencies=[Depends(require_permission("production.edit"))],
)
async def update_order(
    order_id: UUID,
    payload: ProductionOrderUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> ProductionOrderResponse:
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version")
    return ProductionOrderResponse.model_validate(
        await ProductionOrderService(unit_of_work).update_order(
            order_id, data, expected_version=expected_version, actor_id=user_id, user=user
        )
    )


@router.post(
    "/orders/{order_id}/{action}",
    response_model=ProductionOrderResponse,
    dependencies=[Depends(require_permission("production.edit"))],
)
async def order_action(
    order_id: UUID,
    action: str,
    payload: TransitionPayload | None = None,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> ProductionOrderResponse:
    status_by_action = {
        "plan": "planned",
        "release": "released",
        "start": "in_progress",
        "suspend": "suspended",
        "resume": "in_progress",
        "cancel": "cancelled",
    }
    target = status_by_action.get(action, action)
    return ProductionOrderResponse.model_validate(
        await ProductionOrderService(unit_of_work).transition(
            order_id,
            target,
            actor_id=user_id,
            user=user,
            reason=payload.reason if payload else None,
        )
    )
