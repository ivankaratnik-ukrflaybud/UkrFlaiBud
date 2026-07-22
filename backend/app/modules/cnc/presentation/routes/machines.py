from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncMachineService, CncQueryService
from app.modules.cnc.presentation.schemas import (
    CncMachineCreate,
    CncMachineResponse,
    CncMachineUpdate,
    DashboardResponse,
    StatusPayload,
)
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def dashboard(
    organization_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    return await CncQueryService(unit_of_work).dashboard(organization_id, user=user)


@router.get(
    "/machines",
    response_model=PaginatedResponse[CncMachineResponse],
    dependencies=[Depends(require_permission("cnc.machines.read"))],
)
async def list_machines(
    organization_id: UUID | None = None,
    site_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    machine_type: str | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "code",
    sort_direction: SortDirection = SortDirection.ASC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    items, total = await CncMachineService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "site_id": site_id,
            "status": status_filter,
            "machine_type": machine_type,
            "is_active": is_active,
            "search": search,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return PaginatedResponse[CncMachineResponse](
        items=[CncMachineResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/machines",
    response_model=CncMachineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.machines.manage"))],
)
async def create_machine(
    payload: CncMachineCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncMachineResponse.model_validate(
        await CncMachineService(unit_of_work).create(
            payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.get(
    "/machines/{machine_id}",
    response_model=CncMachineResponse,
    dependencies=[Depends(require_permission("cnc.machines.read"))],
)
async def get_machine(
    machine_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    return CncMachineResponse.model_validate(
        await CncMachineService(unit_of_work).get(machine_id, user=user)
    )


@router.patch(
    "/machines/{machine_id}",
    response_model=CncMachineResponse,
    dependencies=[Depends(require_permission("cnc.machines.manage"))],
)
async def update_machine(
    machine_id: UUID,
    payload: CncMachineUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncMachineResponse.model_validate(
        await CncMachineService(unit_of_work).update(
            machine_id, data, expected_version=expected_version, actor_id=user_id, user=user
        )
    )


@router.delete(
    "/machines/{machine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("cnc.machines.manage"))],
)
async def delete_machine(
    machine_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    await CncMachineService(unit_of_work).soft_delete(machine_id, actor_id=user_id, user=user)


@router.post(
    "/machines/{machine_id}/status",
    response_model=CncMachineResponse,
    dependencies=[Depends(require_permission("cnc.machines.manage"))],
)
async def machine_status(
    machine_id: UUID,
    payload: StatusPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncMachineResponse.model_validate(
        await CncMachineService(unit_of_work).set_status(
            machine_id, payload.status, actor_id=user_id, user=user, reason=payload.reason
        )
    )
