from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.modules.production.application.services import StageService
from app.modules.production.presentation.schemas import (
    OrderStageCreate,
    OrderStageResponse,
    StageTemplateCreate,
    StageTemplateResponse,
    StageTransitionPayload,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.post(
    "/stage-templates",
    response_model=StageTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("production.settings"))],
)
async def create_stage_template(
    payload: StageTemplateCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> StageTemplateResponse:
    return StageTemplateResponse.model_validate(
        await StageService(unit_of_work).create_template(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/stage-templates",
    response_model=PaginatedResponse[StageTemplateResponse],
    dependencies=[Depends(require_permission("production.read"))],
)
async def list_stage_templates(
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "default_sequence",
    sort_direction: SortDirection = SortDirection.ASC,
    organization_id: UUID | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[StageTemplateResponse]:
    items, total = await StageService(unit_of_work).list_templates(
        filters={"organization_id": organization_id, "is_active": is_active},
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse[StageTemplateResponse](
        items=[StageTemplateResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/orders/{order_id}/stages",
    response_model=OrderStageResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("production.stages"))],
)
async def add_stage(
    order_id: UUID,
    payload: OrderStageCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> OrderStageResponse:
    return OrderStageResponse.model_validate(
        await StageService(unit_of_work).add_stage(
            order_id, payload.model_dump(exclude_unset=True), actor_id=user_id
        )
    )


@router.get(
    "/orders/{order_id}/stages",
    response_model=list[OrderStageResponse],
    dependencies=[Depends(require_permission("production.read"))],
)
async def list_stages(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> list[OrderStageResponse]:
    return [
        OrderStageResponse.model_validate(stage)
        for stage in await StageService(unit_of_work).list_order_stages(order_id)
    ]


@router.post(
    "/orders/{order_id}/stages/{stage_id}/transition",
    response_model=OrderStageResponse,
    dependencies=[Depends(require_permission("production.stages"))],
)
async def transition_stage(
    order_id: UUID,
    stage_id: UUID,
    payload: StageTransitionPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> OrderStageResponse:
    return OrderStageResponse.model_validate(
        await StageService(unit_of_work).transition_stage(
            order_id,
            stage_id,
            payload.status,
            actor_id=user_id,
            reason=payload.reason,
            notes=payload.notes,
        )
    )
