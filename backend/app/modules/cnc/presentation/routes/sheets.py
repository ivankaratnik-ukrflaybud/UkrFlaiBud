from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncSheetPlanService
from app.modules.cnc.infrastructure.repositories import CncSheetPlanLineRepository
from app.modules.cnc.presentation.schemas import (
    CncSheetPlanCreate,
    CncSheetPlanLineCreate,
    CncSheetPlanLineResponse,
    CncSheetPlanLineUpdate,
    CncSheetPlanResponse,
    CncSheetPlanUpdate,
    CopySheetPlanPayload,
)
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/sheet-plans",
    response_model=PaginatedResponse[CncSheetPlanResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def list_sheet_plans(
    organization_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    material_item_id: UUID | None = None,
    production_order_id: UUID | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "plan_number",
    sort_direction: SortDirection = SortDirection.ASC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
):
    items, total = await CncSheetPlanService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "status": status_filter,
            "material_item_id": material_item_id,
            "production_order_id": production_order_id,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse[CncSheetPlanResponse](
        items=[CncSheetPlanResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/sheet-plans",
    response_model=CncSheetPlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def create_sheet_plan(
    payload: CncSheetPlanCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncSheetPlanResponse.model_validate(
        await CncSheetPlanService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/sheet-plans/{sheet_plan_id}",
    response_model=CncSheetPlanResponse,
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def get_sheet_plan(
    sheet_plan_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    return CncSheetPlanResponse.model_validate(
        await CncSheetPlanService(unit_of_work).get(sheet_plan_id)
    )


@router.patch(
    "/sheet-plans/{sheet_plan_id}",
    response_model=CncSheetPlanResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def update_sheet_plan(
    sheet_plan_id: UUID,
    payload: CncSheetPlanUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncSheetPlanResponse.model_validate(
        await CncSheetPlanService(unit_of_work).update(
            sheet_plan_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.post(
    "/sheet-plans/{sheet_plan_id}/lines",
    response_model=CncSheetPlanLineResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def add_sheet_line(
    sheet_plan_id: UUID,
    payload: CncSheetPlanLineCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncSheetPlanLineResponse.model_validate(
        await CncSheetPlanService(unit_of_work).add_line(
            sheet_plan_id, payload.model_dump(), actor_id=user_id
        )
    )


@router.get(
    "/sheet-plans/{sheet_plan_id}/lines",
    response_model=list[CncSheetPlanLineResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def list_sheet_lines(
    sheet_plan_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    return [
        CncSheetPlanLineResponse.model_validate(item)
        for item in await CncSheetPlanLineRepository(unit_of_work._session).list_for_plan(
            sheet_plan_id
        )
    ]


@router.patch(
    "/sheet-plans/{sheet_plan_id}/lines/{line_id}",
    response_model=CncSheetPlanLineResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def update_sheet_line(
    sheet_plan_id: UUID,
    line_id: UUID,
    payload: CncSheetPlanLineUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncSheetPlanLineResponse.model_validate(
        await CncSheetPlanService(unit_of_work).update_line(
            sheet_plan_id, line_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.delete(
    "/sheet-plans/{sheet_plan_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def delete_sheet_line(
    sheet_plan_id: UUID,
    line_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    await CncSheetPlanService(unit_of_work).delete_line(sheet_plan_id, line_id, actor_id=user_id)


@router.post(
    "/sheet-plans/{sheet_plan_id}/approve",
    response_model=CncSheetPlanResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def approve_sheet_plan(
    sheet_plan_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncSheetPlanResponse.model_validate(
        await CncSheetPlanService(unit_of_work).approve(sheet_plan_id, actor_id=user_id)
    )


@router.post(
    "/sheet-plans/{sheet_plan_id}/copy",
    response_model=CncSheetPlanResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def copy_sheet_plan(
    sheet_plan_id: UUID,
    payload: CopySheetPlanPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncSheetPlanResponse.model_validate(
        await CncSheetPlanService(unit_of_work).copy(
            sheet_plan_id, payload.plan_number, actor_id=user_id
        )
    )
