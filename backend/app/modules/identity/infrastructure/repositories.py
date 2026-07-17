from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.domain.entities import normalize_email
from app.modules.identity.infrastructure.models import (
    LoginAttemptModel,
    PasswordResetTokenModel,
    PermissionModel,
    RoleModel,
    RolePermissionModel,
    UserModel,
    UserRoleModel,
    UserSessionModel,
)
from app.repositories.sqlalchemy import SQLAlchemyRepository
from app.schemas.pagination import SortDirection


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
        total = await self.session.scalar(statement.with_only_columns(func.count()).order_by(None))
        column = self.sortable_fields.get(sort_by, self.sortable_fields["created_at"])
        ordered = statement.order_by(
            column.desc() if sort_direction == SortDirection.DESC else column.asc()
        )
        result = await self.session.scalars(ordered.limit(limit).offset(offset))
        return list(result.all()), total or 0

    def _apply_filters(
        self, statement: Select[tuple[ModelT]], filters: dict[str, object]
    ) -> Select[tuple[ModelT]]:
        return statement


class UserRepository(QueryRepository[UserModel]):
    sortable_fields = {
        "created_at": UserModel.created_at,
        "display_name": UserModel.display_name,
        "email": UserModel.email,
        "is_active": UserModel.is_active,
        "last_login_at": UserModel.last_login_at,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserModel)

    def _apply_filters(
        self, statement: Select[tuple[UserModel]], filters: dict[str, object]
    ) -> Select[tuple[UserModel]]:
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where(
                (UserModel.email.ilike(like)) | (UserModel.display_name.ilike(like))
            )
        if filters.get("is_active") is not None:
            statement = statement.where(UserModel.is_active == filters["is_active"])
        if employee_id := filters.get("employee_id"):
            statement = statement.where(UserModel.employee_id == employee_id)
        return statement

    async def get_by_email(self, email: str, *, include_deleted: bool = False) -> UserModel | None:
        statement = select(UserModel).where(UserModel.normalized_email == normalize_email(email))
        if not include_deleted:
            statement = statement.where(UserModel.deleted_at.is_(None))
        return cast(UserModel | None, await self.session.scalar(statement))

    async def exists_by_email(self, email: str, *, exclude_id: UUID | None = None) -> bool:
        statement = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.normalized_email == normalize_email(email))
        )
        if exclude_id:
            statement = statement.where(UserModel.id != exclude_id)
        return bool(await self.session.scalar(statement))

    async def employee_has_user(self, employee_id: UUID, *, exclude_id: UUID | None = None) -> bool:
        statement = (
            select(func.count())
            .select_from(UserModel)
            .where(UserModel.employee_id == employee_id, UserModel.deleted_at.is_(None))
        )
        if exclude_id:
            statement = statement.where(UserModel.id != exclude_id)
        return bool(await self.session.scalar(statement))


class RoleRepository(QueryRepository[RoleModel]):
    sortable_fields = {
        "created_at": RoleModel.created_at,
        "name": RoleModel.name,
        "code": RoleModel.code,
        "is_system": RoleModel.is_system,
    }

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RoleModel)

    def _apply_filters(
        self, statement: Select[tuple[RoleModel]], filters: dict[str, object]
    ) -> Select[tuple[RoleModel]]:
        if search := filters.get("search"):
            like = f"%{search}%"
            statement = statement.where((RoleModel.name.ilike(like)) | (RoleModel.code.ilike(like)))
        if filters.get("is_active") is not None:
            statement = statement.where(RoleModel.is_active == filters["is_active"])
        return statement

    async def get_by_code(self, code: str) -> RoleModel | None:
        return cast(
            RoleModel | None,
            await self.session.scalar(
                select(RoleModel).where(RoleModel.code == code, RoleModel.deleted_at.is_(None))
            ),
        )

    async def exists_by_code(self, code: str, *, exclude_id: UUID | None = None) -> bool:
        statement = select(func.count()).select_from(RoleModel).where(RoleModel.code == code)
        if exclude_id:
            statement = statement.where(RoleModel.id != exclude_id)
        return bool(await self.session.scalar(statement))


class PermissionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, permission: PermissionModel) -> PermissionModel:
        self.session.add(permission)
        await self.session.flush()
        return permission

    async def list(self) -> list[PermissionModel]:
        result = await self.session.scalars(
            select(PermissionModel).order_by(PermissionModel.module, PermissionModel.name)
        )
        return list(result.all())

    async def get_by_code(self, code: str) -> PermissionModel | None:
        return cast(
            PermissionModel | None,
            await self.session.scalar(select(PermissionModel).where(PermissionModel.code == code)),
        )

    async def get_many(self, permission_ids: Sequence[UUID]) -> Sequence[PermissionModel]:
        result = await self.session.scalars(
            select(PermissionModel).where(PermissionModel.id.in_(permission_ids))
        )
        return list(result.all())


class AssignmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def set_user_roles(
        self, user_id: UUID, role_ids: Sequence[UUID], organization_id: UUID | None = None
    ) -> None:
        await self.session.execute(delete(UserRoleModel).where(UserRoleModel.user_id == user_id))
        for role_id in role_ids:
            self.session.add(
                UserRoleModel(user_id=user_id, role_id=role_id, organization_id=organization_id)
            )
        await self.session.flush()

    async def set_role_permissions(self, role_id: UUID, permission_ids: Sequence[UUID]) -> None:
        await self.session.execute(
            delete(RolePermissionModel).where(RolePermissionModel.role_id == role_id)
        )
        for permission_id in permission_ids:
            self.session.add(RolePermissionModel(role_id=role_id, permission_id=permission_id))
        await self.session.flush()

    async def user_permission_codes(self, user_id: UUID) -> set[str]:
        statement = (
            select(PermissionModel.code)
            .join(RolePermissionModel, RolePermissionModel.permission_id == PermissionModel.id)
            .join(RoleModel, RoleModel.id == RolePermissionModel.role_id)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(
                UserRoleModel.user_id == user_id,
                RoleModel.deleted_at.is_(None),
                RoleModel.is_active.is_(True),
                PermissionModel.is_active.is_(True),
            )
        )
        result = await self.session.scalars(statement)
        return set(result.all())

    async def user_roles(self, user_id: UUID) -> list[RoleModel]:
        statement = (
            select(RoleModel)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .where(UserRoleModel.user_id == user_id, RoleModel.deleted_at.is_(None))
        )
        result = await self.session.scalars(statement)
        return list(result.all())


class SessionRepository(SQLAlchemyRepository[UserSessionModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserSessionModel)

    async def get_active(self, session_id: UUID) -> UserSessionModel | None:
        now = datetime.now(UTC)
        return cast(
            UserSessionModel | None,
            await self.session.scalar(
                select(UserSessionModel).where(
                    UserSessionModel.id == session_id,
                    UserSessionModel.revoked_at.is_(None),
                    UserSessionModel.expires_at > now,
                )
            ),
        )

    async def list_for_user(self, user_id: UUID) -> list[UserSessionModel]:
        result = await self.session.scalars(
            select(UserSessionModel)
            .where(UserSessionModel.user_id == user_id)
            .order_by(UserSessionModel.last_used_at.desc())
        )
        return list(result.all())

    async def revoke_user_sessions(self, user_id: UUID, reason: str) -> None:
        sessions = await self.list_for_user(user_id)
        now = datetime.now(UTC)
        for session in sessions:
            if session.revoked_at is None:
                session.revoked_at = now
                session.revoke_reason = reason
        await self.session.flush()


class LoginAttemptRepository(SQLAlchemyRepository[LoginAttemptModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, LoginAttemptModel)


class PasswordResetTokenRepository(SQLAlchemyRepository[PasswordResetTokenModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, PasswordResetTokenModel)
