from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncPartService
from app.modules.cnc.presentation.schemas import CncPartCreate, CncPartResponse, CncPartUpdate
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/parts",
    response_model=PaginatedResponse[CncPartResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def list_parts(
    organization_id: UUID | None = None,
    material_item_id: UUID | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "code",
    sort_direction: SortDirection = SortDirection.ASC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
):
    items, total = await CncPartService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "material_item_id": material_item_id,
            "is_active": is_active,
            "search": search,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse[CncPartResponse](
        items=[CncPartResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/parts",
    response_model=CncPartResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.work_orders.create"))],
)
async def create_part(
    payload: CncPartCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncPartResponse.model_validate(
        await CncPartService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/parts/{part_id}",
    response_model=CncPartResponse,
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def get_part(part_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)):
    return CncPartResponse.model_validate(await CncPartService(unit_of_work).get(part_id))


@router.patch(
    "/parts/{part_id}",
    response_model=CncPartResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.edit"))],
)
async def update_part(
    part_id: UUID,
    payload: CncPartUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncPartResponse.model_validate(
        await CncPartService(unit_of_work).update(
            part_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.delete(
    "/parts/{part_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("cnc.work_orders.edit"))],
)
async def delete_part(
    part_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    await CncPartService(unit_of_work).soft_delete(part_id, actor_id=user_id)
