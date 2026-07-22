from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncToolService
from app.modules.cnc.presentation.schemas import CncToolCreate, CncToolResponse, CncToolUpdate
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/tools",
    response_model=PaginatedResponse[CncToolResponse],
    dependencies=[Depends(require_permission("cnc.tools.read"))],
)
async def list_tools(
    organization_id: UUID | None = None,
    tool_type: str | None = None,
    is_active: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "code",
    sort_direction: SortDirection = SortDirection.ASC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
):
    items, total = await CncToolService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "tool_type": tool_type,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse[CncToolResponse](
        items=[CncToolResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/tools",
    response_model=CncToolResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.tools.manage"))],
)
async def create_tool(
    payload: CncToolCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncToolResponse.model_validate(
        await CncToolService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.patch(
    "/tools/{tool_id}",
    response_model=CncToolResponse,
    dependencies=[Depends(require_permission("cnc.tools.manage"))],
)
async def update_tool(
    tool_id: UUID,
    payload: CncToolUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncToolResponse.model_validate(
        await CncToolService(unit_of_work).update(
            tool_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.delete(
    "/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("cnc.tools.manage"))],
)
async def delete_tool(
    tool_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    await CncToolService(unit_of_work).soft_delete(tool_id, actor_id=user_id)
