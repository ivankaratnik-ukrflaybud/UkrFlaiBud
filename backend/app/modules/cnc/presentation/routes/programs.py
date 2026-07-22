from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncProgramService
from app.modules.cnc.presentation.schemas import (
    CncProgramCreate,
    CncProgramResponse,
    CncProgramUpdate,
)
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/programs",
    response_model=PaginatedResponse[CncProgramResponse],
    dependencies=[Depends(require_permission("cnc.programs.read"))],
)
async def list_programs(
    organization_id: UUID | None = None,
    program_status: str | None = None,
    machine_type: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "code",
    sort_direction: SortDirection = SortDirection.ASC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
):
    items, total = await CncProgramService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "program_status": program_status,
            "machine_type": machine_type,
            "search": search,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse[CncProgramResponse](
        items=[CncProgramResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/programs",
    response_model=CncProgramResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.programs.manage"))],
)
async def create_program(
    payload: CncProgramCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncProgramResponse.model_validate(
        await CncProgramService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/programs/{program_id}",
    response_model=CncProgramResponse,
    dependencies=[Depends(require_permission("cnc.programs.read"))],
)
async def get_program(
    program_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    return CncProgramResponse.model_validate(await CncProgramService(unit_of_work).get(program_id))


@router.patch(
    "/programs/{program_id}",
    response_model=CncProgramResponse,
    dependencies=[Depends(require_permission("cnc.programs.manage"))],
)
async def update_program(
    program_id: UUID,
    payload: CncProgramUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncProgramResponse.model_validate(
        await CncProgramService(unit_of_work).update(
            program_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.post(
    "/programs/{program_id}/approve",
    response_model=CncProgramResponse,
    dependencies=[Depends(require_permission("cnc.programs.manage"))],
)
async def approve_program(
    program_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncProgramResponse.model_validate(
        await CncProgramService(unit_of_work).approve(program_id, actor_id=user_id)
    )


@router.post(
    "/programs/{program_id}/obsolete",
    response_model=CncProgramResponse,
    dependencies=[Depends(require_permission("cnc.programs.manage"))],
)
async def obsolete_program(
    program_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    return CncProgramResponse.model_validate(
        await CncProgramService(unit_of_work).obsolete(program_id, actor_id=user_id)
    )


@router.post(
    "/programs/{program_id}/attachments",
    response_model=CncProgramResponse,
    dependencies=[Depends(require_permission("cnc.programs.manage"))],
)
async def attach_program_metadata(
    program_id: UUID,
    payload: CncProgramUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    data = payload.model_dump(
        exclude_unset=True,
        include={"source_file_name", "storage_key", "checksum", "file_type", "version"},
    )
    expected_version = data.pop("version", None)
    return CncProgramResponse.model_validate(
        await CncProgramService(unit_of_work).update(
            program_id, data, expected_version=expected_version, actor_id=user_id
        )
    )
