from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dependencies import get_unit_of_work
from app.modules.identity.presentation.dependencies import require_permission
from app.modules.organizations.application.services import (
    DepartmentService,
    EmployeeService,
    OrganizationService,
    PositionService,
)
from app.modules.organizations.domain.entities import EmployeeStatus
from app.modules.organizations.presentation.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
    EmployeeCreate,
    EmployeeResponse,
    EmployeeUpdate,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    PositionCreate,
    PositionResponse,
    PositionUpdate,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()
UnitOfWorkDependency = Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)]
SortDirectionQuery = Annotated[SortDirection, Query()]


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("organizations.manage"))],
)
async def create_organization(
    payload: OrganizationCreate,
    unit_of_work: UnitOfWorkDependency,
) -> OrganizationResponse:
    organization = await OrganizationService(unit_of_work).create(payload.model_dump())
    return OrganizationResponse.model_validate(organization)


@router.get(
    "/organizations",
    response_model=PaginatedResponse[OrganizationResponse],
    dependencies=[Depends(require_permission("organizations.read"))],
)
async def list_organizations(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    name: str | None = None,
    edrpou: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[OrganizationResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await OrganizationService(unit_of_work).list(
        filters={"name": name, "edrpou": edrpou, "is_active": is_active},
        page=page_request,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse(
        items=[OrganizationResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission("organizations.read"))],
)
async def get_organization(
    organization_id: UUID,
    unit_of_work: UnitOfWorkDependency,
) -> OrganizationResponse:
    organization = await OrganizationService(unit_of_work).get(organization_id)
    return OrganizationResponse.model_validate(organization)


@router.patch(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    dependencies=[Depends(require_permission("organizations.manage"))],
)
async def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    unit_of_work: UnitOfWorkDependency,
) -> OrganizationResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    organization = await OrganizationService(unit_of_work).update(
        organization_id,
        data,
        expected_version=version,
    )
    return OrganizationResponse.model_validate(organization)


@router.delete(
    "/organizations/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("organizations.manage"))],
)
async def delete_organization(
    organization_id: UUID,
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    await OrganizationService(unit_of_work).soft_delete(organization_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("departments.manage"))],
)
async def create_department(
    payload: DepartmentCreate,
    unit_of_work: UnitOfWorkDependency,
) -> DepartmentResponse:
    department = await DepartmentService(unit_of_work).create(payload.model_dump())
    return DepartmentResponse.model_validate(department)


@router.get(
    "/departments",
    response_model=PaginatedResponse[DepartmentResponse],
    dependencies=[Depends(require_permission("departments.read"))],
)
async def list_departments(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    parent_department_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[DepartmentResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await DepartmentService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "parent_department_id": parent_department_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=page_request,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse(
        items=[DepartmentResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
    dependencies=[Depends(require_permission("departments.read"))],
)
async def get_department(
    department_id: UUID,
    unit_of_work: UnitOfWorkDependency,
) -> DepartmentResponse:
    department = await DepartmentService(unit_of_work).get(department_id)
    return DepartmentResponse.model_validate(department)


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
    dependencies=[Depends(require_permission("departments.manage"))],
)
async def update_department(
    department_id: UUID,
    payload: DepartmentUpdate,
    unit_of_work: UnitOfWorkDependency,
) -> DepartmentResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    department = await DepartmentService(unit_of_work).update(
        department_id,
        data,
        expected_version=version,
    )
    return DepartmentResponse.model_validate(department)


@router.delete(
    "/departments/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("departments.manage"))],
)
async def delete_department(
    department_id: UUID,
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    await DepartmentService(unit_of_work).soft_delete(department_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/positions",
    response_model=PositionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("positions.manage"))],
)
async def create_position(
    payload: PositionCreate,
    unit_of_work: UnitOfWorkDependency,
) -> PositionResponse:
    position = await PositionService(unit_of_work).create(payload.model_dump())
    return PositionResponse.model_validate(position)


@router.get(
    "/positions",
    response_model=PaginatedResponse[PositionResponse],
    dependencies=[Depends(require_permission("positions.read"))],
)
async def list_positions(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    department_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[PositionResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await PositionService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "department_id": department_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=page_request,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse(
        items=[PositionResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/positions/{position_id}",
    response_model=PositionResponse,
    dependencies=[Depends(require_permission("positions.read"))],
)
async def get_position(position_id: UUID, unit_of_work: UnitOfWorkDependency) -> PositionResponse:
    position = await PositionService(unit_of_work).get(position_id)
    return PositionResponse.model_validate(position)


@router.patch(
    "/positions/{position_id}",
    response_model=PositionResponse,
    dependencies=[Depends(require_permission("positions.manage"))],
)
async def update_position(
    position_id: UUID,
    payload: PositionUpdate,
    unit_of_work: UnitOfWorkDependency,
) -> PositionResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    position = await PositionService(unit_of_work).update(
        position_id, data, expected_version=version
    )
    return PositionResponse.model_validate(position)


@router.delete(
    "/positions/{position_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("positions.manage"))],
)
async def delete_position(position_id: UUID, unit_of_work: UnitOfWorkDependency) -> Response:
    await PositionService(unit_of_work).soft_delete(position_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("employees.manage"))],
)
async def create_employee(
    payload: EmployeeCreate,
    unit_of_work: UnitOfWorkDependency,
) -> EmployeeResponse:
    employee = await EmployeeService(unit_of_work).create(payload.model_dump())
    return EmployeeResponse.model_validate(employee)


@router.get(
    "/employees",
    response_model=PaginatedResponse[EmployeeResponse],
    dependencies=[Depends(require_permission("employees.read"))],
)
async def list_employees(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    department_id: UUID | None = None,
    position_id: UUID | None = None,
    supervisor_employee_id: UUID | None = None,
    status: EmployeeStatus | None = None,
    name: str | None = None,
) -> PaginatedResponse[EmployeeResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await EmployeeService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "department_id": department_id,
            "position_id": position_id,
            "supervisor_employee_id": supervisor_employee_id,
            "status": status,
            "name": name,
        },
        page=page_request,
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return PaginatedResponse(
        items=[EmployeeResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(require_permission("employees.read"))],
)
async def get_employee(employee_id: UUID, unit_of_work: UnitOfWorkDependency) -> EmployeeResponse:
    employee = await EmployeeService(unit_of_work).get(employee_id)
    return EmployeeResponse.model_validate(employee)


@router.patch(
    "/employees/{employee_id}",
    response_model=EmployeeResponse,
    dependencies=[Depends(require_permission("employees.manage"))],
)
async def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    unit_of_work: UnitOfWorkDependency,
) -> EmployeeResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    employee = await EmployeeService(unit_of_work).update(
        employee_id, data, expected_version=version
    )
    return EmployeeResponse.model_validate(employee)


@router.delete(
    "/employees/{employee_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("employees.manage"))],
)
async def delete_employee(employee_id: UUID, unit_of_work: UnitOfWorkDependency) -> Response:
    await EmployeeService(unit_of_work).soft_delete(employee_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
