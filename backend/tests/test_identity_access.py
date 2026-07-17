from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_unit_of_work
from app.core.config import settings
from app.main import create_app
from app.models.base import ConflictError, PermissionDeniedError, ValidationError
from app.modules.identity.application.security import verify_password
from app.modules.identity.application.services import (
    PERMISSIONS,
    ROLE_TEMPLATES,
    AuthService,
    IdentityService,
    UserService,
)
from app.modules.identity.infrastructure.models import (
    LoginAttemptModel,
    PermissionModel,
    RoleModel,
    UserModel,
    UserSessionModel,
)
from app.modules.identity.infrastructure.repositories import RoleRepository, UserRepository
from app.modules.organizations.application.services import (
    DepartmentService,
    EmployeeService,
    OrganizationService,
    PositionService,
)
from app.modules.organizations.domain.entities import EmployeeStatus


class UnitOfWorkStub:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._session = session

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


async def seed_identity(db_session: AsyncSession) -> None:
    async with service_context(db_session) as unit_of_work:
        await IdentityService(unit_of_work).seed_system_access()


async def create_employee(db_session: AsyncSession):
    async with service_context(db_session) as unit_of_work:
        organization = await OrganizationService(unit_of_work).create(
            {
                "name": "UkrFlyBud",
                "short_name": "UFB",
                "legal_name": "UkrFlyBud LLC",
                "edrpou": "12345678",
                "is_active": True,
            }
        )
        department = await DepartmentService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "name": "Operations",
                "code": "OPS",
                "is_active": True,
            }
        )
        position = await PositionService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "department_id": department.id,
                "name": "Dispatcher",
                "code": "DSP",
                "is_active": True,
            }
        )
        return await EmployeeService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "department_id": department.id,
                "position_id": position.id,
                "personnel_number": "E-100",
                "first_name": "Ivan",
                "last_name": "Petrenko",
                "status": EmployeeStatus.ACTIVE,
            }
        )


async def test_seed_system_access_and_bootstrap_admin(db_session: AsyncSession) -> None:
    async with service_context(db_session) as unit_of_work:
        await IdentityService(unit_of_work).bootstrap_admin()

    permission_count = await db_session.scalar(select(func.count()).select_from(PermissionModel))
    role_count = await db_session.scalar(select(func.count()).select_from(RoleModel))
    admin = await UserRepository(db_session).get_by_email(settings.bootstrap_admin_email or "")

    assert permission_count == len(PERMISSIONS)
    assert role_count == len(ROLE_TEMPLATES)
    assert admin is not None
    assert admin.is_superuser is True
    assert admin.must_change_password is True
    assert settings.bootstrap_admin_password is not None
    assert admin.password_hash != settings.bootstrap_admin_password
    assert verify_password(settings.bootstrap_admin_password, admin.password_hash)


async def test_user_lifecycle_login_lockout_and_sessions(db_session: AsyncSession) -> None:
    await seed_identity(db_session)
    employee = await create_employee(db_session)

    async with service_context(db_session) as unit_of_work:
        employee_role = await RoleRepository(db_session).get_by_code("employee")
        assert employee_role is not None
        user, temporary_password = await UserService(unit_of_work).create(
            {
                "email": "pilot@example.com",
                "display_name": "Pilot User",
                "employee_id": employee.id,
                "temporary_password": "StartPass123!",
                "role_ids": [employee_role.id],
            }
        )
        assert temporary_password == "StartPass123!"
        assert user.password_hash != temporary_password

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await UserService(unit_of_work).create(
                {
                    "email": "second@example.com",
                    "display_name": "Second User",
                    "employee_id": employee.id,
                    "temporary_password": "StartPass123!",
                }
            )

    for _ in range(settings.auth_failed_login_limit):
        async with service_context(db_session) as unit_of_work:
            with pytest.raises(ValidationError):
                await AuthService(unit_of_work).login(
                    email="pilot@example.com",
                    password="wrong",
                    ip_address="127.0.0.1",
                    user_agent="pytest",
                )

    locked_user = await UserRepository(db_session).get_by_email("pilot@example.com")
    assert locked_user is not None
    assert locked_user.locked_until is not None

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(PermissionDeniedError):
            await AuthService(unit_of_work).login(
                email="pilot@example.com",
                password="StartPass123!",
                ip_address="127.0.0.1",
                user_agent="pytest",
            )
        await UserService(unit_of_work).unlock(locked_user.id)

    async with service_context(db_session) as unit_of_work:
        access, refresh, session, login_user = await AuthService(unit_of_work).login(
            email="pilot@example.com",
            password="StartPass123!",
            ip_address="127.0.0.1",
            user_agent="Mozilla Firefox",
        )
        assert access
        assert login_user.failed_login_attempts == 0
        assert session.device_name == "Firefox"
        assert session.refresh_token_hash != refresh

    async with service_context(db_session) as unit_of_work:
        new_access, new_refresh, _, _ = await AuthService(unit_of_work).refresh(session.id, refresh)
        assert new_access
        assert new_refresh != refresh

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(PermissionDeniedError):
            await AuthService(unit_of_work).refresh(session.id, refresh)

    revoked = await db_session.get(UserSessionModel, session.id)
    assert revoked is not None
    assert revoked.revoked_at is not None

    attempt_count = await db_session.scalar(select(func.count()).select_from(LoginAttemptModel))
    assert attempt_count == settings.auth_failed_login_limit + 2


async def test_password_change_reset_and_protected_api(db_session: AsyncSession) -> None:
    await seed_identity(db_session)
    async with service_context(db_session) as unit_of_work:
        await IdentityService(unit_of_work).bootstrap_admin()
        viewer, _ = await UserService(unit_of_work).create(
            {
                "email": "viewer@example.com",
                "display_name": "Viewer User",
                "temporary_password": "ViewerPass123!",
            }
        )
        await AuthService(unit_of_work).change_password(
            viewer.id, "ViewerPass123!", "ViewerPass124!"
        )

    app = create_app()

    async def override_unit_of_work() -> AsyncGenerator[UnitOfWorkStub]:
        async with service_context(db_session) as unit_of_work:
            yield unit_of_work

    app.dependency_overrides[get_unit_of_work] = override_unit_of_work
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        viewer_login = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "ViewerPass124!"},
        )
        assert viewer_login.status_code == 200
        assert "password_hash" not in viewer_login.text
        assert "temporary_password" not in viewer_login.text
        viewer_token = viewer_login.json()["access_token"]

        forbidden = await client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {viewer_token}"}
        )
        assert forbidden.status_code == 403
        assert forbidden.json()["code"] == "permission_denied"

        admin_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": settings.bootstrap_admin_email,
                "password": settings.bootstrap_admin_password,
            },
        )
        assert admin_login.status_code == 200
        admin_token = admin_login.json()["access_token"]

        users = await client.get(
            "/api/v1/users", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert users.status_code == 200
        assert users.json()["total"] >= 2

        sessions = await client.get(
            f"/api/v1/users/{viewer.id}/sessions",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert sessions.status_code == 200

    async with service_context(db_session) as unit_of_work:
        reset_password = await UserService(unit_of_work).reset_password(viewer.id)
        assert reset_password

    refreshed_viewer = await db_session.get(UserModel, viewer.id)
    assert refreshed_viewer is not None
    assert refreshed_viewer.must_change_password is True
