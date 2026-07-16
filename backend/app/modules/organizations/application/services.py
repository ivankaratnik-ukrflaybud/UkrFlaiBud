from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ConflictError, EntityNotFoundError, ValidationError
from app.modules.organizations.domain.entities import EmployeeStatus
from app.modules.organizations.infrastructure.models import (
    DepartmentModel,
    EmployeeModel,
    OrganizationModel,
    PositionModel,
)
from app.modules.organizations.infrastructure.repositories import (
    SQLAlchemyDepartmentRepository,
    SQLAlchemyEmployeeRepository,
    SQLAlchemyOrganizationRepository,
    SQLAlchemyPositionRepository,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection


class BaseOrganizationService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def _commit(self) -> None:
        await self.unit_of_work.commit()

    @staticmethod
    def _ensure_version(entity: Any, expected_version: int | None) -> None:
        if expected_version is not None and entity.version != expected_version:
            raise ConflictError(
                "Entity version conflict.",
                details={"expected_version": expected_version, "current_version": entity.version},
            )


class OrganizationService(BaseOrganizationService):
    async def create(self, data: dict[str, Any]) -> OrganizationModel:
        repository = SQLAlchemyOrganizationRepository(self.session)
        if await repository.exists_by_edrpou(data["edrpou"]):
            raise ConflictError("Organization EDRPOU must be unique.", {"field": "edrpou"})
        organization = await repository.create(OrganizationModel(**data))
        await self._commit()
        return organization

    async def get(
        self, organization_id: UUID, *, include_deleted: bool = False
    ) -> OrganizationModel:
        organization = await SQLAlchemyOrganizationRepository(self.session).get(
            organization_id,
            include_deleted=include_deleted,
        )
        if organization is None:
            raise EntityNotFoundError("Organization not found.", {"id": str(organization_id)})
        return organization

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[OrganizationModel], int]:
        return await SQLAlchemyOrganizationRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        organization_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> OrganizationModel:
        repository = SQLAlchemyOrganizationRepository(self.session)
        organization = await self.get(organization_id)
        self._ensure_version(organization, expected_version)
        if data.get("edrpou") and await repository.exists_by_edrpou(
            data["edrpou"],
            exclude_id=organization_id,
        ):
            raise ConflictError("Organization EDRPOU must be unique.", {"field": "edrpou"})
        _apply_updates(organization, data)
        await repository.update(organization)
        await self._commit()
        return organization

    async def soft_delete(self, organization_id: UUID) -> None:
        repository = SQLAlchemyOrganizationRepository(self.session)
        await self.get(organization_id)
        await repository.soft_delete(organization_id)
        await self._commit()

    async def restore(
        self, organization_id: UUID, *, expected_version: int | None = None
    ) -> OrganizationModel:
        repository = SQLAlchemyOrganizationRepository(self.session)
        organization = await self.get(organization_id, include_deleted=True)
        self._ensure_version(organization, expected_version)
        organization.deleted_at = None
        organization.deleted_by = None
        await repository.update(organization)
        await self._commit()
        return organization


class DepartmentService(BaseOrganizationService):
    async def create(self, data: dict[str, Any]) -> DepartmentModel:
        repository = SQLAlchemyDepartmentRepository(self.session)
        await self._ensure_organization_exists(data["organization_id"])
        await self._validate_parent_department(
            organization_id=data["organization_id"],
            department_id=None,
            parent_department_id=data.get("parent_department_id"),
        )
        await self._validate_manager(data["organization_id"], data.get("manager_employee_id"))
        if data.get("code") and await repository.exists_by_code(
            data["organization_id"], data["code"]
        ):
            raise ConflictError(
                "Department code must be unique within organization.", {"field": "code"}
            )
        department = await repository.create(DepartmentModel(**data))
        await self._commit()
        return department

    async def get(self, department_id: UUID, *, include_deleted: bool = False) -> DepartmentModel:
        department = await SQLAlchemyDepartmentRepository(self.session).get(
            department_id,
            include_deleted=include_deleted,
        )
        if department is None:
            raise EntityNotFoundError("Department not found.", {"id": str(department_id)})
        return department

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[DepartmentModel], int]:
        return await SQLAlchemyDepartmentRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        department_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> DepartmentModel:
        repository = SQLAlchemyDepartmentRepository(self.session)
        department = await self.get(department_id)
        self._ensure_version(department, expected_version)
        organization_id = data.get("organization_id", department.organization_id)
        await self._ensure_organization_exists(organization_id)
        await self._validate_parent_department(
            organization_id=organization_id,
            department_id=department_id,
            parent_department_id=data.get("parent_department_id", department.parent_department_id),
        )
        await self._validate_manager(
            organization_id, data.get("manager_employee_id", department.manager_employee_id)
        )
        code = data.get("code", department.code)
        if code and await repository.exists_by_code(
            organization_id, code, exclude_id=department_id
        ):
            raise ConflictError(
                "Department code must be unique within organization.", {"field": "code"}
            )
        _apply_updates(department, data)
        await repository.update(department)
        await self._commit()
        return department

    async def soft_delete(self, department_id: UUID) -> None:
        repository = SQLAlchemyDepartmentRepository(self.session)
        await self.get(department_id)
        await repository.soft_delete(department_id)
        await self._commit()

    async def restore(
        self, department_id: UUID, *, expected_version: int | None = None
    ) -> DepartmentModel:
        repository = SQLAlchemyDepartmentRepository(self.session)
        department = await self.get(department_id, include_deleted=True)
        self._ensure_version(department, expected_version)
        department.deleted_at = None
        department.deleted_by = None
        await repository.update(department)
        await self._commit()
        return department

    async def _ensure_organization_exists(self, organization_id: UUID) -> None:
        await OrganizationService(self.unit_of_work).get(organization_id)

    async def _validate_parent_department(
        self,
        *,
        organization_id: UUID,
        department_id: UUID | None,
        parent_department_id: UUID | None,
    ) -> None:
        if parent_department_id is None:
            return
        if department_id == parent_department_id:
            raise ValidationError("Department cannot be its own parent.")
        parent = await self.get(parent_department_id)
        if parent.organization_id != organization_id:
            raise ValidationError("Parent department must belong to the same organization.")
        while parent.parent_department_id is not None:
            if parent.parent_department_id == department_id:
                raise ValidationError("Department hierarchy cannot contain cycles.")
            parent = await self.get(parent.parent_department_id)
            if parent.organization_id != organization_id:
                raise ValidationError("Parent department must belong to the same organization.")

    async def _validate_manager(
        self, organization_id: UUID, manager_employee_id: UUID | None
    ) -> None:
        if manager_employee_id is None:
            return
        manager = await EmployeeService(self.unit_of_work).get(manager_employee_id)
        if manager.organization_id != organization_id:
            raise ValidationError("Department manager must belong to the same organization.")


class PositionService(BaseOrganizationService):
    async def create(self, data: dict[str, Any]) -> PositionModel:
        repository = SQLAlchemyPositionRepository(self.session)
        await self._validate_ownership(data["organization_id"], data.get("department_id"))
        if data.get("code") and await repository.exists_by_code(
            data["organization_id"], data["code"]
        ):
            raise ConflictError(
                "Position code must be unique within organization.", {"field": "code"}
            )
        position = await repository.create(PositionModel(**data))
        await self._commit()
        return position

    async def get(self, position_id: UUID, *, include_deleted: bool = False) -> PositionModel:
        position = await SQLAlchemyPositionRepository(self.session).get(
            position_id,
            include_deleted=include_deleted,
        )
        if position is None:
            raise EntityNotFoundError("Position not found.", {"id": str(position_id)})
        return position

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[PositionModel], int]:
        return await SQLAlchemyPositionRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        position_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> PositionModel:
        repository = SQLAlchemyPositionRepository(self.session)
        position = await self.get(position_id)
        self._ensure_version(position, expected_version)
        organization_id = data.get("organization_id", position.organization_id)
        await self._validate_ownership(
            organization_id, data.get("department_id", position.department_id)
        )
        code = data.get("code", position.code)
        if code and await repository.exists_by_code(organization_id, code, exclude_id=position_id):
            raise ConflictError(
                "Position code must be unique within organization.", {"field": "code"}
            )
        _apply_updates(position, data)
        await repository.update(position)
        await self._commit()
        return position

    async def soft_delete(self, position_id: UUID) -> None:
        repository = SQLAlchemyPositionRepository(self.session)
        await self.get(position_id)
        await repository.soft_delete(position_id)
        await self._commit()

    async def restore(
        self, position_id: UUID, *, expected_version: int | None = None
    ) -> PositionModel:
        repository = SQLAlchemyPositionRepository(self.session)
        position = await self.get(position_id, include_deleted=True)
        self._ensure_version(position, expected_version)
        position.deleted_at = None
        position.deleted_by = None
        await repository.update(position)
        await self._commit()
        return position

    async def _validate_ownership(self, organization_id: UUID, department_id: UUID | None) -> None:
        await OrganizationService(self.unit_of_work).get(organization_id)
        if department_id is None:
            return
        department = await DepartmentService(self.unit_of_work).get(department_id)
        if department.organization_id != organization_id:
            raise ValidationError("Position department must belong to the same organization.")


class EmployeeService(BaseOrganizationService):
    async def create(self, data: dict[str, Any]) -> EmployeeModel:
        repository = SQLAlchemyEmployeeRepository(self.session)
        await self._validate_ownership(
            data["organization_id"],
            data.get("department_id"),
            data.get("position_id"),
            data.get("supervisor_employee_id"),
            employee_id=None,
        )
        if data.get("personnel_number") and await repository.exists_by_personnel_number(
            data["organization_id"],
            data["personnel_number"],
        ):
            raise ConflictError(
                "Employee personnel number must be unique within organization.",
                {"field": "personnel_number"},
            )
        employee = await repository.create(EmployeeModel(**data))
        await self._commit()
        return employee

    async def get(self, employee_id: UUID, *, include_deleted: bool = False) -> EmployeeModel:
        employee = await SQLAlchemyEmployeeRepository(self.session).get(
            employee_id,
            include_deleted=include_deleted,
        )
        if employee is None:
            raise EntityNotFoundError("Employee not found.", {"id": str(employee_id)})
        return employee

    async def list(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[EmployeeModel], int]:
        return await SQLAlchemyEmployeeRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self,
        employee_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
    ) -> EmployeeModel:
        repository = SQLAlchemyEmployeeRepository(self.session)
        employee = await self.get(employee_id)
        self._ensure_version(employee, expected_version)
        organization_id = data.get("organization_id", employee.organization_id)
        await self._validate_ownership(
            organization_id,
            data.get("department_id", employee.department_id),
            data.get("position_id", employee.position_id),
            data.get("supervisor_employee_id", employee.supervisor_employee_id),
            employee_id=employee_id,
        )
        personnel_number = data.get("personnel_number", employee.personnel_number)
        if personnel_number and await repository.exists_by_personnel_number(
            organization_id,
            personnel_number,
            exclude_id=employee_id,
        ):
            raise ConflictError(
                "Employee personnel number must be unique within organization.",
                {"field": "personnel_number"},
            )
        if data.get("status") and data["status"] not in {status.value for status in EmployeeStatus}:
            raise ValidationError("Invalid employee status.", {"field": "status"})
        _apply_updates(employee, data)
        await repository.update(employee)
        await self._commit()
        return employee

    async def soft_delete(self, employee_id: UUID) -> None:
        repository = SQLAlchemyEmployeeRepository(self.session)
        await self.get(employee_id)
        await repository.soft_delete(employee_id)
        await self._commit()

    async def restore(
        self, employee_id: UUID, *, expected_version: int | None = None
    ) -> EmployeeModel:
        repository = SQLAlchemyEmployeeRepository(self.session)
        employee = await self.get(employee_id, include_deleted=True)
        self._ensure_version(employee, expected_version)
        employee.deleted_at = None
        employee.deleted_by = None
        await repository.update(employee)
        await self._commit()
        return employee

    async def _validate_ownership(
        self,
        organization_id: UUID,
        department_id: UUID | None,
        position_id: UUID | None,
        supervisor_employee_id: UUID | None,
        *,
        employee_id: UUID | None,
    ) -> None:
        await OrganizationService(self.unit_of_work).get(organization_id)
        if supervisor_employee_id is not None and supervisor_employee_id == employee_id:
            raise ValidationError("Employee supervisor cannot reference the same employee.")
        if department_id is not None:
            department = await DepartmentService(self.unit_of_work).get(department_id)
            if department.organization_id != organization_id:
                raise ValidationError("Employee department must belong to the same organization.")
        if position_id is not None:
            position = await PositionService(self.unit_of_work).get(position_id)
            if position.organization_id != organization_id:
                raise ValidationError("Employee position must belong to the same organization.")
            if department_id is not None and position.department_id not in (None, department_id):
                raise ValidationError("Employee position must belong to the selected department.")
        if supervisor_employee_id is not None:
            supervisor = await self.get(supervisor_employee_id)
            if supervisor.organization_id != organization_id:
                raise ValidationError("Employee supervisor must belong to the same organization.")


def _apply_updates(entity: Any, data: dict[str, Any]) -> None:
    for field, value in data.items():
        setattr(entity, field, value)
