from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.organizations.infrastructure.models import (
    DepartmentModel,
    EmployeeModel,
    OrganizationModel,
    PositionModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection

ModelT = OrganizationModel | DepartmentModel | PositionModel | EmployeeModel


class QueryRepository[ModelT]:
    sortable_fields: dict[str, Any] = {}

    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model
        self.base_repository = SQLAlchemyRepository(session, model)

    async def create(self, entity: ModelT) -> ModelT:
        return await self.base_repository.create(entity)

    async def get(self, entity_id: UUID, *, include_deleted: bool = False) -> ModelT | None:
        return await self.base_repository.get(entity_id, include_deleted=include_deleted)

    async def update(self, entity: ModelT) -> ModelT:
        return await self.base_repository.update(entity)

    async def soft_delete(self, entity_id: UUID) -> None:
        await self.base_repository.soft_delete(entity_id)

    async def list(
        self,
        *,
        filters: dict[str, object],
        sort_by: str,
        sort_direction: SortDirection,
        limit: int,
        offset: int,
        include_deleted: bool = False,
    ) -> tuple[list[ModelT], int]:
        statement = self._apply_filters(
            self.base_repository._exclude_deleted(select(self.model), include_deleted),
            filters,
        )
        total_statement = statement.with_only_columns(func.count()).order_by(None)
        total = await self.session.scalar(total_statement)
        sort_column = self.sortable_fields.get(sort_by, self.sortable_fields["created_at"])
        ordered = statement.order_by(
            sort_column.desc() if sort_direction == SortDirection.DESC else sort_column.asc()
        )
        result = await self.session.scalars(ordered.limit(limit).offset(offset))
        return list(result.all()), total or 0

    async def exists(self, *conditions: Any) -> bool:
        statement = select(func.count()).select_from(self.model).where(and_(*conditions))
        count = await self.session.scalar(statement)
        return bool(count)

    def _apply_filters(
        self,
        statement: Select[tuple[ModelT]],
        filters: dict[str, object],
    ) -> Select[tuple[ModelT]]:
        return statement


class SQLAlchemyOrganizationRepository(QueryRepository[OrganizationModel]):
    sortable_fields = {
        "created_at": OrganizationModel.created_at,
        "name": OrganizationModel.name,
        "edrpou": OrganizationModel.edrpou,
        "is_active": OrganizationModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, OrganizationModel)

    def _apply_filters(
        self,
        statement: Select[tuple[OrganizationModel]],
        filters: dict[str, object],
    ) -> Select[tuple[OrganizationModel]]:
        if name := filters.get("name"):
            statement = statement.where(OrganizationModel.name.ilike(f"%{name}%"))
        if edrpou := filters.get("edrpou"):
            statement = statement.where(OrganizationModel.edrpou == edrpou)
        if filters.get("is_active") is not None:
            statement = statement.where(OrganizationModel.is_active == filters["is_active"])
        return statement

    async def exists_by_edrpou(self, edrpou: str, *, exclude_id: UUID | None = None) -> bool:
        conditions: list[Any] = [OrganizationModel.edrpou == edrpou]
        if exclude_id is not None:
            conditions.append(OrganizationModel.id != exclude_id)
        return await self.exists(*conditions)


class SQLAlchemyDepartmentRepository(QueryRepository[DepartmentModel]):
    sortable_fields = {
        "created_at": DepartmentModel.created_at,
        "name": DepartmentModel.name,
        "code": DepartmentModel.code,
        "is_active": DepartmentModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, DepartmentModel)

    def _apply_filters(
        self,
        statement: Select[tuple[DepartmentModel]],
        filters: dict[str, object],
    ) -> Select[tuple[DepartmentModel]]:
        return _apply_common_org_filters(statement, DepartmentModel, filters)

    async def exists_by_code(
        self,
        organization_id: UUID,
        code: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        conditions: list[Any] = [
            DepartmentModel.organization_id == organization_id,
            DepartmentModel.code == code,
        ]
        if exclude_id is not None:
            conditions.append(DepartmentModel.id != exclude_id)
        return await self.exists(*conditions)


class SQLAlchemyPositionRepository(QueryRepository[PositionModel]):
    sortable_fields = {
        "created_at": PositionModel.created_at,
        "name": PositionModel.name,
        "code": PositionModel.code,
        "is_active": PositionModel.is_active,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PositionModel)

    def _apply_filters(
        self,
        statement: Select[tuple[PositionModel]],
        filters: dict[str, object],
    ) -> Select[tuple[PositionModel]]:
        statement = _apply_common_org_filters(statement, PositionModel, filters)
        if department_id := filters.get("department_id"):
            statement = statement.where(PositionModel.department_id == department_id)
        return statement

    async def exists_by_code(
        self,
        organization_id: UUID,
        code: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        conditions: list[Any] = [
            PositionModel.organization_id == organization_id,
            PositionModel.code == code,
        ]
        if exclude_id is not None:
            conditions.append(PositionModel.id != exclude_id)
        return await self.exists(*conditions)


class SQLAlchemyEmployeeRepository(QueryRepository[EmployeeModel]):
    sortable_fields = {
        "created_at": EmployeeModel.created_at,
        "last_name": EmployeeModel.last_name,
        "first_name": EmployeeModel.first_name,
        "status": EmployeeModel.status,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, EmployeeModel)

    def _apply_filters(
        self,
        statement: Select[tuple[EmployeeModel]],
        filters: dict[str, object],
    ) -> Select[tuple[EmployeeModel]]:
        if organization_id := filters.get("organization_id"):
            statement = statement.where(EmployeeModel.organization_id == organization_id)
        if department_id := filters.get("department_id"):
            statement = statement.where(EmployeeModel.department_id == department_id)
        if position_id := filters.get("position_id"):
            statement = statement.where(EmployeeModel.position_id == position_id)
        if supervisor_id := filters.get("supervisor_employee_id"):
            statement = statement.where(EmployeeModel.supervisor_employee_id == supervisor_id)
        if status := filters.get("status"):
            statement = statement.where(EmployeeModel.status == status)
        if name := filters.get("name"):
            like_name = f"%{name}%"
            statement = statement.where(
                or_(
                    EmployeeModel.first_name.ilike(like_name),
                    EmployeeModel.last_name.ilike(like_name),
                    EmployeeModel.middle_name.ilike(like_name),
                )
            )
        return statement

    async def exists_by_personnel_number(
        self,
        organization_id: UUID,
        personnel_number: str,
        *,
        exclude_id: UUID | None = None,
    ) -> bool:
        conditions: list[Any] = [
            EmployeeModel.organization_id == organization_id,
            EmployeeModel.personnel_number == personnel_number,
        ]
        if exclude_id is not None:
            conditions.append(EmployeeModel.id != exclude_id)
        return await self.exists(*conditions)


def _apply_common_org_filters(
    statement: Select[tuple[Any]],
    model: Any,
    filters: dict[str, object],
) -> Select[tuple[Any]]:
    if organization_id := filters.get("organization_id"):
        statement = statement.where(model.organization_id == organization_id)
    if parent_department_id := filters.get("parent_department_id"):
        statement = statement.where(model.parent_department_id == parent_department_id)
    if name := filters.get("name"):
        statement = statement.where(model.name.ilike(f"%{name}%"))
    if code := filters.get("code"):
        statement = statement.where(model.code == code)
    if filters.get("is_active") is not None:
        statement = statement.where(model.is_active == filters["is_active"])
    return statement
