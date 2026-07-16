from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_unit_of_work
from app.main import create_app
from app.models.base import ConflictError, ValidationError
from app.modules.organizations.application.services import (
    DepartmentService,
    EmployeeService,
    OrganizationService,
    PositionService,
)
from app.modules.organizations.domain.entities import EmployeeStatus
from app.modules.organizations.infrastructure.repositories import (
    SQLAlchemyDepartmentRepository,
    SQLAlchemyEmployeeRepository,
)
from app.schemas.pagination import PageRequest, SortDirection


class UnitOfWorkStub:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, entity: object, attribute_names: list[str] | None = None) -> None:
        await self.session.refresh(entity, attribute_names=attribute_names)


@asynccontextmanager
async def service_context(db_session: AsyncSession) -> AsyncGenerator[UnitOfWorkStub]:
    unit_of_work = UnitOfWorkStub(db_session)
    try:
        yield unit_of_work
    except Exception:
        await unit_of_work.rollback()
        raise


async def create_core_records(db_session: AsyncSession):
    async with service_context(db_session) as unit_of_work:
        organization = await OrganizationService(unit_of_work).create(
            {
                "name": "ТОВ Українські дрони",
                "short_name": "УкрДрони",
                "legal_name": "Товариство з обмеженою відповідальністю Українські дрони",
                "edrpou": "12345678",
                "is_active": True,
            }
        )
        department = await DepartmentService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "name": "Виробництво",
                "code": "PROD",
                "is_active": True,
            }
        )
        position = await PositionService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "department_id": department.id,
                "name": "Інженер",
                "code": "ENG",
                "is_active": True,
            }
        )
        employee = await EmployeeService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "department_id": department.id,
                "position_id": position.id,
                "personnel_number": "E-001",
                "first_name": "Іван",
                "last_name": "Петренко",
                "status": EmployeeStatus.ACTIVE,
            }
        )
    return organization, department, position, employee


async def test_crud_soft_delete_restore_and_optimistic_locking(db_session: AsyncSession) -> None:
    organization, department, position, employee = await create_core_records(db_session)

    async with service_context(db_session) as unit_of_work:
        updated_org = await OrganizationService(unit_of_work).update(
            organization.id,
            {"short_name": "УКРД"},
            expected_version=organization.version,
        )
        updated_department = await DepartmentService(unit_of_work).update(
            department.id,
            {"description": "Основний виробничий підрозділ"},
            expected_version=department.version,
        )
        updated_position = await PositionService(unit_of_work).update(
            position.id,
            {"description": "Інженерна посада"},
            expected_version=position.version,
        )
        updated_employee = await EmployeeService(unit_of_work).update(
            employee.id,
            {"status": EmployeeStatus.ON_LEAVE},
            expected_version=employee.version,
        )

    assert updated_org.short_name == "УКРД"
    assert updated_department.description is not None
    assert updated_position.description is not None
    assert updated_employee.status == EmployeeStatus.ON_LEAVE

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await OrganizationService(unit_of_work).update(
                organization.id,
                {"name": "Конфлікт"},
                expected_version=1,
            )
        await EmployeeService(unit_of_work).soft_delete(employee.id)
        deleted_employee = await EmployeeService(unit_of_work).get(
            employee.id, include_deleted=True
        )
        deleted_at = deleted_employee.deleted_at
        restored_employee = await EmployeeService(unit_of_work).restore(employee.id)

    assert deleted_at is not None
    assert restored_employee.deleted_at is None


async def test_repository_filtering_sorting_and_pagination(db_session: AsyncSession) -> None:
    organization, department, _, employee = await create_core_records(db_session)

    department_repository = SQLAlchemyDepartmentRepository(db_session)
    employee_repository = SQLAlchemyEmployeeRepository(db_session)
    departments, total_departments = await department_repository.list(
        filters={"organization_id": organization.id, "code": "PROD"},
        sort_by="name",
        sort_direction=SortDirection.ASC,
        limit=10,
        offset=0,
    )
    employees, total_employees = await employee_repository.list(
        filters={"organization_id": organization.id, "name": "Петренко"},
        sort_by="last_name",
        sort_direction=SortDirection.ASC,
        limit=1,
        offset=0,
    )

    assert total_departments == 1
    assert departments[0].id == department.id
    assert total_employees == 1
    assert employees[0].id == employee.id


async def test_uniqueness_constraints(db_session: AsyncSession) -> None:
    organization, department, _, _ = await create_core_records(db_session)

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await OrganizationService(unit_of_work).create(
                {
                    "name": "Дублікат",
                    "short_name": "Дуб",
                    "legal_name": "Дублікат",
                    "edrpou": organization.edrpou,
                    "is_active": True,
                }
            )
        with pytest.raises(ConflictError):
            await DepartmentService(unit_of_work).create(
                {
                    "organization_id": organization.id,
                    "name": "Інший підрозділ",
                    "code": department.code,
                    "is_active": True,
                }
            )


async def test_department_cycle_and_cross_organization_validation(db_session: AsyncSession) -> None:
    organization, department, position, employee = await create_core_records(db_session)

    async with service_context(db_session) as unit_of_work:
        other_organization = await OrganizationService(unit_of_work).create(
            {
                "name": "Інша організація",
                "short_name": "Інша",
                "legal_name": "Інша організація",
                "edrpou": "87654321",
                "is_active": True,
            }
        )
        other_department = await DepartmentService(unit_of_work).create(
            {
                "organization_id": other_organization.id,
                "name": "Інший підрозділ",
                "code": "OTHER",
                "is_active": True,
            }
        )

        with pytest.raises(ValidationError):
            await DepartmentService(unit_of_work).update(
                department.id,
                {"parent_department_id": department.id},
                expected_version=department.version,
            )
        with pytest.raises(ValidationError):
            await DepartmentService(unit_of_work).update(
                department.id,
                {"parent_department_id": other_department.id},
                expected_version=department.version,
            )
        with pytest.raises(ValidationError):
            await PositionService(unit_of_work).update(
                position.id,
                {"department_id": other_department.id},
                expected_version=position.version,
            )
        with pytest.raises(ValidationError):
            await EmployeeService(unit_of_work).update(
                employee.id,
                {"department_id": other_department.id},
                expected_version=employee.version,
            )


async def test_employee_self_supervisor_and_cross_organization_position(
    db_session: AsyncSession,
) -> None:
    _, _, position, employee = await create_core_records(db_session)

    async with service_context(db_session) as unit_of_work:
        other_organization = await OrganizationService(unit_of_work).create(
            {
                "name": "Організація позиції",
                "short_name": "Позиція",
                "legal_name": "Організація позиції",
                "edrpou": "11223344",
                "is_active": True,
            }
        )
        other_position = await PositionService(unit_of_work).create(
            {
                "organization_id": other_organization.id,
                "name": "Інша посада",
                "code": "OTHER-POS",
                "is_active": True,
            }
        )

        with pytest.raises(ValidationError):
            await EmployeeService(unit_of_work).update(
                employee.id,
                {"supervisor_employee_id": employee.id},
                expected_version=employee.version,
            )
        with pytest.raises(ValidationError):
            await EmployeeService(unit_of_work).update(
                employee.id,
                {"position_id": other_position.id},
                expected_version=employee.version,
            )
        with pytest.raises(ConflictError):
            await PositionService(unit_of_work).update(
                position.id,
                {"name": "Застаріла версія"},
                expected_version=999,
            )


async def test_service_pagination(db_session: AsyncSession) -> None:
    await create_core_records(db_session)
    async with service_context(db_session) as unit_of_work:
        items, total = await OrganizationService(unit_of_work).list(
            filters={},
            page=PageRequest(page=1, page_size=1),
            sort_by="name",
            sort_direction=SortDirection.ASC,
        )

    assert total == 1
    assert len(items) == 1


async def test_openapi_route_registration_and_api_error_format(db_session: AsyncSession) -> None:
    app = create_app()

    async def override_unit_of_work() -> AsyncGenerator[UnitOfWorkStub]:
        async with service_context(db_session) as unit_of_work:
            yield unit_of_work

    app.dependency_overrides[get_unit_of_work] = override_unit_of_work
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        openapi_response = await client.get("/openapi.json")
        not_found_response = await client.get(
            "/api/v1/organizations/00000000-0000-0000-0000-000000000001"
        )

    paths = openapi_response.json()["paths"]
    assert "/api/v1/organizations" in paths
    assert "/api/v1/departments" in paths
    assert "/api/v1/positions" in paths
    assert "/api/v1/employees" in paths
    assert not_found_response.status_code == 404
    assert not_found_response.json()["code"] == "entity_not_found"
