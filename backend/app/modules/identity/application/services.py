from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.base import (
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.modules.identity.application.security import (
    create_access_token,
    generate_refresh_token,
    generate_temporary_password,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.identity.domain.entities import normalize_email, validate_password_strength
from app.modules.identity.infrastructure.models import (
    LoginAttemptModel,
    PermissionModel,
    RoleModel,
    UserModel,
    UserRoleModel,
    UserSessionModel,
)
from app.modules.identity.infrastructure.repositories import (
    AssignmentRepository,
    LoginAttemptRepository,
    PermissionRepository,
    RoleRepository,
    SessionRepository,
    UserRepository,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection

PERMISSIONS: dict[str, tuple[str, str, str]] = {
    "organizations.read": ("Організації", "Перегляд організацій", "organizations"),
    "organizations.manage": (
        "Керування організаціями",
        "Створення та редагування організацій",
        "organizations",
    ),
    "departments.read": ("Підрозділи", "Перегляд підрозділів", "organizations"),
    "departments.manage": (
        "Керування підрозділами",
        "Створення та редагування підрозділів",
        "organizations",
    ),
    "positions.read": ("Посади", "Перегляд посад", "organizations"),
    "positions.manage": ("Керування посадами", "Створення та редагування посад", "organizations"),
    "employees.read": ("Працівники", "Перегляд працівників", "organizations"),
    "employees.manage": (
        "Керування працівниками",
        "Створення та редагування працівників",
        "organizations",
    ),
    "users.read": ("Користувачі", "Перегляд користувачів", "identity"),
    "users.manage": (
        "Керування користувачами",
        "Створення та редагування користувачів",
        "identity",
    ),
    "roles.read": ("Ролі", "Перегляд ролей", "identity"),
    "roles.manage": ("Керування ролями", "Редагування ролей та доступу", "identity"),
    "sessions.manage": ("Сеанси", "Керування активними пристроями", "identity"),
    "audit.read": ("Журнал дій", "Перегляд журналу дій", "audit"),
    "settings.manage": ("Налаштування", "Керування налаштуваннями", "settings"),
    "inventory.sites.read": ("Майданчики", "Перегляд майданчиків", "inventory"),
    "inventory.sites.manage": (
        "Керування майданчиками",
        "Створення та редагування майданчиків",
        "inventory",
    ),
    "inventory.warehouses.read": ("Склади", "Перегляд складів", "inventory"),
    "inventory.warehouses.manage": (
        "Керування складами",
        "Створення та редагування складів",
        "inventory",
    ),
    "inventory.locations.read": ("Місця зберігання", "Перегляд місць зберігання", "inventory"),
    "inventory.locations.manage": (
        "Керування місцями зберігання",
        "Створення та редагування місць зберігання",
        "inventory",
    ),
    "inventory.units.read": ("Одиниці виміру", "Перегляд одиниць виміру", "inventory"),
    "inventory.units.manage": (
        "Керування одиницями виміру",
        "Створення та редагування одиниць виміру",
        "inventory",
    ),
    "inventory.categories.read": (
        "Категорії номенклатури",
        "Перегляд категорій номенклатури",
        "inventory",
    ),
    "inventory.categories.manage": (
        "Керування категоріями",
        "Створення та редагування категорій номенклатури",
        "inventory",
    ),
    "inventory.items.read": ("Номенклатура", "Перегляд номенклатури", "inventory"),
    "inventory.items.manage": (
        "Керування номенклатурою",
        "Створення та редагування номенклатури",
        "inventory",
    ),
    "inventory.tracking.read": (
        "Партії та серійні номери",
        "Перегляд партій і серійних номерів",
        "inventory",
    ),
    "inventory.tracking.manage": (
        "Керування відстеженням",
        "Створення партій та серійних номерів",
        "inventory",
    ),
    "inventory.documents.read": (
        "Складські документи",
        "Перегляд складських документів",
        "inventory",
    ),
    "inventory.documents.create": (
        "Створення складських документів",
        "Створення чернеток складських документів",
        "inventory",
    ),
    "inventory.documents.edit": (
        "Редагування складських документів",
        "Редагування чернеток складських документів",
        "inventory",
    ),
    "inventory.documents.post": (
        "Проведення складських документів",
        "Проведення складських документів",
        "inventory",
    ),
    "inventory.documents.cancel": (
        "Скасування складських документів",
        "Скасування та сторнування складських документів",
        "inventory",
    ),
    "inventory.stock.read": ("Залишки", "Перегляд складських залишків", "inventory"),
    "inventory.stock.adjust": (
        "Коригування залишків",
        "Створення складських коригувань",
        "inventory",
    ),
    "inventory.audit.read": ("Аудит складу", "Перегляд складського аудиту", "inventory"),
    "bom.read": ("Специфікації", "Перегляд специфікацій і версій", "bom"),
    "bom.create": (
        "Створення специфікацій",
        "Створення специфікацій і нових версій BOM",
        "bom",
    ),
    "bom.edit": (
        "Редагування специфікацій",
        "Редагування чернеток специфікацій, версій і позицій",
        "bom",
    ),
    "bom.approve": (
        "Затвердження специфікацій",
        "Затвердження та архівування версій специфікацій",
        "bom",
    ),
    "bom.specifications.read": ("Специфікації", "Перегляд специфікацій і версій", "bom"),
    "bom.specifications.create": (
        "Створення специфікацій",
        "Створення нових специфікацій виробів",
        "bom",
    ),
    "bom.specifications.edit": (
        "Редагування специфікацій",
        "Редагування реквізитів специфікацій",
        "bom",
    ),
    "bom.specifications.delete": (
        "Архівування специфікацій",
        "Архівування та деактивація специфікацій",
        "bom",
    ),
    "bom.versions.create": (
        "Створення версій специфікацій",
        "Створення нових версій на основі чинних специфікацій",
        "bom",
    ),
    "bom.versions.edit": (
        "Редагування версій специфікацій",
        "Редагування чернеток версій і позицій",
        "bom",
    ),
    "bom.versions.review": (
        "Перегляд версій специфікацій",
        "Передавання версій специфікацій на перегляд",
        "bom",
    ),
    "bom.versions.approve": (
        "Затвердження специфікацій",
        "Затвердження та заміна версій специфікацій",
        "bom",
    ),
    "bom.export": ("Експорт специфікацій", "Завантаження PDF та Excel", "bom"),
    "bom.import": ("Імпорт специфікацій", "Імпорт позицій із XLSX", "bom"),
    "bom.attachments": (
        "Файли специфікацій",
        "Керування кресленнями, фото та іншими файлами специфікацій",
        "bom",
    ),
    "bom.attachments.manage": (
        "Файли специфікацій",
        "Керування кресленнями, фото та іншими файлами специфікацій",
        "bom",
    ),
    "bom.audit.read": ("Аудит специфікацій", "Перегляд аудиту специфікацій", "bom"),
    "production.read": ("Виробництво", "Перегляд виробничих замовлень", "production"),
    "production.create": (
        "Створення замовлень",
        "Створення виробничих замовлень",
        "production",
    ),
    "production.edit": (
        "Редагування замовлень",
        "Планування, випуск і зміна виробничих замовлень",
        "production",
    ),
    "production.reserve": (
        "Резервування матеріалів",
        "Резервування та зняття резерву матеріалів",
        "production",
    ),
    "production.issue": (
        "Видача матеріалів",
        "Видача і повернення матеріалів виробництва",
        "production",
    ),
    "production.consume": (
        "Списання матеріалів",
        "Фіксація використання і браку матеріалів",
        "production",
    ),
    "production.stages": (
        "Етапи виробництва",
        "Керування етапами виробничих замовлень",
        "production",
    ),
    "production.complete": (
        "Готова продукція",
        "Оприбуткування готової продукції",
        "production",
    ),
    "production.export": ("Експорт виробництва", "PDF та Excel виробничих замовлень", "production"),
    "production.settings": (
        "Налаштування виробництва",
        "Керування шаблонами етапів",
        "production",
    ),
}

BOM_PERMISSION_ALIASES: dict[str, tuple[str, ...]] = {
    "bom.read": ("bom.specifications.read",),
    "bom.create": ("bom.specifications.create", "bom.versions.create"),
    "bom.edit": (
        "bom.specifications.edit",
        "bom.specifications.delete",
        "bom.versions.edit",
        "bom.versions.review",
    ),
    "bom.approve": ("bom.versions.approve",),
    "bom.attachments": ("bom.attachments.manage",),
}

ROLE_TEMPLATES: dict[str, tuple[str, str, list[str]]] = {
    "system_admin": ("Системний адміністратор", "Повний доступ до системи.", list(PERMISSIONS)),
    "director": (
        "Директор",
        "Повний робочий доступ, користувачі, ролі та журнал дій.",
        [code for code in PERMISSIONS if code != "settings.manage"],
    ),
    "department_manager": (
        "Керівник підрозділу",
        "Перегляд структури та базове керування працівниками.",
        [
            "organizations.read",
            "departments.read",
            "positions.read",
            "employees.read",
            "employees.manage",
        ],
    ),
    "employee": (
        "Працівник",
        "Базовий перегляд організаційної інформації.",
        ["organizations.read", "departments.read", "positions.read", "employees.read"],
    ),
    "viewer": (
        "Перегляд",
        "Тільки перегляд без змін.",
        [
            "organizations.read",
            "departments.read",
            "positions.read",
            "employees.read",
            "users.read",
            "roles.read",
        ],
    ),
    "warehouse_clerk": (
        "Комірник",
        "Операційна робота зі складськими документами та залишками.",
        [
            "inventory.sites.read",
            "inventory.warehouses.read",
            "inventory.locations.read",
            "inventory.units.read",
            "inventory.categories.read",
            "inventory.items.read",
            "inventory.tracking.read",
            "inventory.documents.read",
            "inventory.documents.create",
            "inventory.documents.edit",
            "inventory.documents.post",
            "inventory.stock.read",
        ],
    ),
    "warehouse_manager": (
        "Керівник складу",
        "Керування складськими довідниками, документами та доступом.",
        [
            code
            for code in PERMISSIONS
            if code.startswith("inventory.") and code != "inventory.audit.read"
        ],
    ),
    "warehouse_viewer": (
        "Перегляд складу",
        "Перегляд складських довідників, документів і залишків без змін.",
        [
            "inventory.sites.read",
            "inventory.warehouses.read",
            "inventory.locations.read",
            "inventory.units.read",
            "inventory.categories.read",
            "inventory.items.read",
            "inventory.tracking.read",
            "inventory.documents.read",
            "inventory.stock.read",
        ],
    ),
    "bom_designer": (
        "Конструктор",
        "Створення та редагування чернеток специфікацій і позицій.",
        [
            "bom.read",
            "bom.create",
            "bom.edit",
            "bom.export",
            "bom.import",
            "bom.attachments",
            "inventory.items.read",
            "inventory.units.read",
        ],
    ),
    "bom_technologist": (
        "Технолог",
        "Підготовка, перевірка та імпорт технологічних специфікацій.",
        [
            "bom.read",
            "bom.create",
            "bom.edit",
            "bom.export",
            "bom.import",
            "bom.attachments",
            "inventory.items.read",
            "inventory.units.read",
        ],
    ),
    "bom_viewer": (
        "Перегляд специфікацій",
        "Перегляд, друк та експорт специфікацій без змін.",
        ["bom.read", "bom.export"],
    ),
    "bom_approver": (
        "Затвердження специфікацій",
        "Перегляд, погодження і затвердження версій специфікацій.",
        [
            "bom.read",
            "bom.approve",
            "bom.export",
        ],
    ),
    "production_manager": (
        "Керівник виробництва",
        "Повний операційний доступ до виробничих замовлень.",
        [code for code in PERMISSIONS if code.startswith("production.")],
    ),
}


class IdentityService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def seed_system_access(self) -> None:
        permission_repository = PermissionRepository(self.session)
        role_repository = RoleRepository(self.session)
        assignment_repository = AssignmentRepository(self.session)
        permission_by_code: dict[str, PermissionModel] = {}
        for code, (name, description, module) in PERMISSIONS.items():
            permission = await permission_repository.get_by_code(code)
            if permission is None:
                permission = await permission_repository.create(
                    PermissionModel(code=code, name=name, description=description, module=module)
                )
            permission_by_code[code] = permission
        for code, (name, description, permission_codes) in ROLE_TEMPLATES.items():
            role = await role_repository.get_by_code(code)
            if role is None:
                role = await role_repository.create(
                    RoleModel(
                        name=name,
                        code=code,
                        description=description,
                        is_system=True,
                        is_active=True,
                    )
                )
            await assignment_repository.set_role_permissions(
                role.id,
                [permission_by_code[permission_code].id for permission_code in permission_codes],
            )
        await self.unit_of_work.commit()

    async def bootstrap_admin(self) -> None:
        await self.seed_system_access()
        if not (
            settings.bootstrap_admin_email
            and settings.bootstrap_admin_name
            and settings.bootstrap_admin_password
        ):
            return
        user_repository = UserRepository(self.session)
        existing = await user_repository.get_by_email(settings.bootstrap_admin_email)
        if existing is not None:
            await self._ensure_system_admin_role(existing.id)
            await self.unit_of_work.commit()
            return
        validate_password_strength(settings.bootstrap_admin_password)
        admin = await user_repository.create(
            UserModel(
                email=settings.bootstrap_admin_email,
                normalized_email=normalize_email(settings.bootstrap_admin_email),
                password_hash=hash_password(settings.bootstrap_admin_password),
                display_name=settings.bootstrap_admin_name,
                is_active=True,
                is_superuser=True,
                must_change_password=True,
            )
        )
        admin_role = await RoleRepository(self.session).get_by_code("system_admin")
        if admin_role is not None:
            await AssignmentRepository(self.session).set_user_roles(admin.id, [admin_role.id])
        await self.unit_of_work.commit()

    async def _ensure_system_admin_role(self, user_id: UUID) -> None:
        admin_role = await RoleRepository(self.session).get_by_code("system_admin")
        if admin_role is None:
            return
        assignment_repository = AssignmentRepository(self.session)
        roles = await assignment_repository.user_roles(user_id)
        if all(role.id != admin_role.id for role in roles):
            self.session.add(UserRoleModel(user_id=user_id, role_id=admin_role.id))
            await self.session.flush()


class AuthService(IdentityService):
    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None,
        user_agent: str | None,
    ) -> tuple[str, str, UserSessionModel, UserModel]:
        user_repository = UserRepository(self.session)
        user = await user_repository.get_by_email(email)
        generic_error = ValidationError("Invalid email or password.", {"field": "email"})
        if user is None:
            await self._record_attempt(
                email=email,
                user=None,
                success=False,
                reason="invalid_credentials",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.unit_of_work.commit()
            raise generic_error
        now = datetime.now(UTC)
        if not user.is_active:
            await self._record_attempt(
                email=email,
                user=user,
                success=False,
                reason="inactive",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.unit_of_work.commit()
            raise PermissionDeniedError("User account is inactive.")
        if user.locked_until and user.locked_until > now:
            await self._record_attempt(
                email=email,
                user=user,
                success=False,
                reason="locked",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.unit_of_work.commit()
            raise PermissionDeniedError("User account is locked.")
        if not verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.auth_failed_login_limit:
                user.locked_until = now + timedelta(minutes=settings.auth_lock_minutes)
            await user_repository.update(user)
            await self._record_attempt(
                email=email,
                user=user,
                success=False,
                reason="invalid_credentials",
                ip_address=ip_address,
                user_agent=user_agent,
            )
            await self.unit_of_work.commit()
            raise generic_error
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        await user_repository.update(user)
        refresh_token = generate_refresh_token()
        session = await SessionRepository(self.session).create(
            UserSessionModel(
                user_id=user.id,
                refresh_token_hash=hash_token(refresh_token),
                device_name=_device_name(user_agent),
                ip_address=ip_address,
                user_agent=user_agent,
                last_used_at=now,
                expires_at=now + timedelta(days=settings.auth_refresh_token_days),
            )
        )
        await self._record_attempt(
            email=email,
            user=user,
            success=True,
            reason=None,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        access_token = create_access_token(
            user.id, await AssignmentRepository(self.session).user_permission_codes(user.id)
        )
        await self.unit_of_work.commit()
        return access_token, refresh_token, session, user

    async def refresh(
        self, session_id: UUID, refresh_token: str
    ) -> tuple[str, str, UserSessionModel, UserModel]:
        session_repository = SessionRepository(self.session)
        session = await session_repository.get_active(session_id)
        if session is None:
            raise PermissionDeniedError("Session is not active.")
        if session.refresh_token_hash != hash_token(refresh_token):
            session.revoked_at = datetime.now(UTC)
            session.revoke_reason = "refresh token reuse"
            await self.unit_of_work.commit()
            raise PermissionDeniedError("Session is not active.")
        user = await UserService(self.unit_of_work).get(session.user_id)
        new_refresh = generate_refresh_token()
        session.refresh_token_hash = hash_token(new_refresh)
        session.last_used_at = datetime.now(UTC)
        await session_repository.update(session)
        access = create_access_token(
            user.id, await AssignmentRepository(self.session).user_permission_codes(user.id)
        )
        await self.unit_of_work.commit()
        return access, new_refresh, session, user

    async def logout(self, session_id: UUID, reason: str = "logout") -> None:
        session = await SessionRepository(self.session).get(session_id)
        if session is not None and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            session.revoke_reason = reason
            await self.unit_of_work.commit()

    async def logout_all(self, user_id: UUID) -> None:
        await SessionRepository(self.session).revoke_user_sessions(user_id, "logout all")
        await self.unit_of_work.commit()

    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> None:
        validate_password_strength(new_password)
        user = await UserService(self.unit_of_work).get(user_id)
        if not verify_password(current_password, user.password_hash):
            raise ValidationError("Invalid current password.", {"field": "current_password"})
        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        await UserRepository(self.session).update(user)
        await self.unit_of_work.commit()

    async def _record_attempt(
        self,
        *,
        email: str,
        user: UserModel | None,
        success: bool,
        reason: str | None,
        ip_address: str | None,
        user_agent: str | None,
    ) -> None:
        await LoginAttemptRepository(self.session).create(
            LoginAttemptModel(
                email=normalize_email(email),
                user_id=user.id if user else None,
                success=success,
                failure_reason=reason,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        )


class UserService(IdentityService):
    async def create(self, data: dict[str, Any]) -> tuple[UserModel, str | None]:
        repository = UserRepository(self.session)
        email = data.pop("email")
        if await repository.exists_by_email(email):
            raise ConflictError("User email must be unique.", {"field": "email"})
        employee_id = data.get("employee_id")
        if employee_id and await repository.employee_has_user(employee_id):
            raise ConflictError("Employee already has an active user.", {"field": "employee_id"})
        password = data.pop("temporary_password", None) or generate_temporary_password()
        validate_password_strength(password)
        role_ids = data.pop("role_ids", [])
        user = await repository.create(
            UserModel(
                **data,
                email=email,
                normalized_email=normalize_email(email),
                password_hash=hash_password(password),
                must_change_password=True,
            )
        )
        if role_ids:
            await AssignmentRepository(self.session).set_user_roles(user.id, role_ids)
        await self.unit_of_work.commit()
        return user, password

    async def get(self, user_id: UUID, *, include_deleted: bool = False) -> UserModel:
        user = await UserRepository(self.session).get(user_id, include_deleted=include_deleted)
        if user is None:
            raise EntityNotFoundError("User not found.", {"id": str(user_id)})
        return user

    async def list(
        self,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[UserModel], int]:
        return await UserRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self, user_id: UUID, data: dict[str, Any], expected_version: int | None
    ) -> UserModel:
        repository = UserRepository(self.session)
        user = await self.get(user_id)
        if expected_version and user.version != expected_version:
            raise ConflictError(
                "User version conflict.",
                {"expected_version": expected_version, "current_version": user.version},
            )
        if "email" in data and await repository.exists_by_email(data["email"], exclude_id=user_id):
            raise ConflictError("User email must be unique.", {"field": "email"})
        if (
            "employee_id" in data
            and data["employee_id"]
            and await repository.employee_has_user(data["employee_id"], exclude_id=user_id)
        ):
            raise ConflictError("Employee already has an active user.", {"field": "employee_id"})
        for key, value in data.items():
            setattr(user, key, value)
        if "email" in data:
            user.normalized_email = normalize_email(data["email"])
        await repository.update(user)
        await self.unit_of_work.commit()
        return user

    async def set_active(self, user_id: UUID, active: bool) -> UserModel:
        user = await self.get(user_id)
        user.is_active = active
        await UserRepository(self.session).update(user)
        if not active:
            await SessionRepository(self.session).revoke_user_sessions(user.id, "deactivated")
        await self.unit_of_work.commit()
        return user

    async def soft_delete(self, user_id: UUID) -> None:
        await UserRepository(self.session).soft_delete(user_id)
        await SessionRepository(self.session).revoke_user_sessions(user_id, "deleted")
        await self.unit_of_work.commit()

    async def unlock(self, user_id: UUID) -> UserModel:
        user = await self.get(user_id)
        user.failed_login_attempts = 0
        user.locked_until = None
        await UserRepository(self.session).update(user)
        await self.unit_of_work.commit()
        return user

    async def reset_password(self, user_id: UUID) -> str:
        user = await self.get(user_id)
        password = generate_temporary_password()
        user.password_hash = hash_password(password)
        user.must_change_password = True
        await UserRepository(self.session).update(user)
        await SessionRepository(self.session).revoke_user_sessions(user_id, "password reset")
        await self.unit_of_work.commit()
        return password

    async def set_roles(self, user_id: UUID, role_ids: Sequence[UUID]) -> UserModel:
        user = await self.get(user_id)
        await AssignmentRepository(self.session).set_user_roles(user_id, role_ids)
        await self.unit_of_work.commit()
        return user


class RoleService(IdentityService):
    async def create(self, data: dict[str, Any]) -> RoleModel:
        if await RoleRepository(self.session).exists_by_code(data["code"]):
            raise ConflictError("Role code must be unique.", {"field": "code"})
        role = await RoleRepository(self.session).create(RoleModel(**data, is_system=False))
        await self.unit_of_work.commit()
        return role

    async def get(self, role_id: UUID) -> RoleModel:
        role = await RoleRepository(self.session).get(role_id)
        if role is None:
            raise EntityNotFoundError("Role not found.", {"id": str(role_id)})
        return role

    async def list(
        self,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[RoleModel], int]:
        return await RoleRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update(
        self, role_id: UUID, data: dict[str, Any], expected_version: int | None
    ) -> RoleModel:
        role = await self.get(role_id)
        if role.is_system and ("code" in data or "is_system" in data):
            raise ValidationError("System roles cannot be changed this way.")
        if expected_version and role.version != expected_version:
            raise ConflictError(
                "Role version conflict.",
                {"expected_version": expected_version, "current_version": role.version},
            )
        for key, value in data.items():
            setattr(role, key, value)
        await RoleRepository(self.session).update(role)
        await self.unit_of_work.commit()
        return role

    async def soft_delete(self, role_id: UUID) -> None:
        role = await self.get(role_id)
        if role.is_system:
            raise ValidationError("System roles cannot be deleted.")
        await RoleRepository(self.session).soft_delete(role_id)
        await self.unit_of_work.commit()

    async def set_permissions(self, role_id: UUID, permission_ids: Sequence[UUID]) -> RoleModel:
        role = await self.get(role_id)
        if role.is_system:
            raise ValidationError("System role permissions are managed by the system.")
        await AssignmentRepository(self.session).set_role_permissions(role.id, permission_ids)
        await self.unit_of_work.commit()
        return role


async def require_permission_for_user(
    unit_of_work: SQLAlchemyUnitOfWork, user_id: UUID, permission_code: str
) -> None:
    user = await UserService(unit_of_work).get(user_id)
    if user.is_superuser:
        return
    permission_codes = set(
        await AssignmentRepository(unit_of_work._session).user_permission_codes(user_id)
    )
    if permission_code in permission_codes:
        return
    if any(alias in permission_codes for alias in BOM_PERMISSION_ALIASES.get(permission_code, ())):
        return
    raise PermissionDeniedError("Not enough permissions.")


def _device_name(user_agent: str | None) -> str | None:
    if not user_agent:
        return None
    if "Firefox" in user_agent:
        return "Firefox"
    if "Chrome" in user_agent:
        return "Chrome"
    if "Safari" in user_agent:
        return "Safari"
    return "Браузер"
