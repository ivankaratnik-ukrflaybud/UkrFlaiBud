from typing import Annotated, Literal, cast
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response, status

from app.api.dependencies import get_unit_of_work
from app.core.config import settings
from app.models.base import PermissionDeniedError
from app.modules.identity.application.services import (
    AuthService,
    IdentityService,
    RoleService,
    UserService,
)
from app.modules.identity.infrastructure.repositories import PermissionRepository, SessionRepository
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.modules.identity.presentation.schemas import (
    ChangePasswordRequest,
    CreatedUserResponse,
    LoginRequest,
    PasswordResetResponse,
    PermissionAssignmentRequest,
    PermissionResponse,
    RoleAssignmentRequest,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()
UnitOfWorkDependency = Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)]
RefreshCookie = Annotated[str | None, Cookie(alias="refresh_token")]
SessionCookie = Annotated[str | None, Cookie(alias="session_id")]


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest, request: Request, response: Response, unit_of_work: UnitOfWorkDependency
) -> TokenResponse:
    access, refresh, session, user = await AuthService(unit_of_work).login(
        email=str(payload.email),
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_auth_cookies(response, refresh, str(session.id))
    return TokenResponse(access_token=access, user=UserResponse.model_validate(user))


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    unit_of_work: UnitOfWorkDependency,
    refresh_token: RefreshCookie = None,
    session_id: SessionCookie = None,
) -> TokenResponse:
    if not refresh_token or not session_id:
        raise PermissionDeniedError("Session is not active.")
    access, new_refresh, session, user = await AuthService(unit_of_work).refresh(
        UUID(session_id), refresh_token
    )
    _set_auth_cookies(response, new_refresh, str(session.id))
    return TokenResponse(access_token=access, user=UserResponse.model_validate(user))


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response, unit_of_work: UnitOfWorkDependency, session_id: SessionCookie = None
) -> Response:
    if session_id:
        await AuthService(unit_of_work).logout(UUID(session_id))
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    user_id: Annotated[UUID, Depends(current_user_id)],
    response: Response,
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    await AuthService(unit_of_work).logout_all(user_id)
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/auth/me", response_model=UserResponse)
async def me(user: Annotated[object, Depends(current_user)]) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    payload: ChangePasswordRequest,
    user_id: Annotated[UUID, Depends(current_user_id)],
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    await AuthService(unit_of_work).change_password(
        user_id, payload.current_password, payload.new_password
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/auth/sessions", response_model=list[SessionResponse])
async def own_sessions(
    user_id: Annotated[UUID, Depends(current_user_id)],
    unit_of_work: UnitOfWorkDependency,
) -> list[SessionResponse]:
    sessions = await SessionRepository(unit_of_work._session).list_for_user(user_id)
    return [SessionResponse.model_validate(session) for session in sessions]


@router.delete("/auth/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_own_session(
    session_id: UUID,
    user_id: Annotated[UUID, Depends(current_user_id)],
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    session = await SessionRepository(unit_of_work._session).get(session_id)
    if session is None or session.user_id != user_id:
        raise PermissionDeniedError("Session is not active.")
    await AuthService(unit_of_work).logout(session_id, "own revoke")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users",
    response_model=CreatedUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def create_user(
    payload: UserCreate, unit_of_work: UnitOfWorkDependency
) -> CreatedUserResponse:
    user, password = await UserService(unit_of_work).create(payload.model_dump())
    return CreatedUserResponse(user=UserResponse.model_validate(user), temporary_password=password)


@router.get(
    "/users",
    response_model=PaginatedResponse[UserResponse],
    dependencies=[Depends(require_permission("users.read"))],
)
async def list_users(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirection = SortDirection.DESC,
    search: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[UserResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await UserService(unit_of_work).list(
        {"search": search, "is_active": is_active}, page_request, sort_by, sort_direction
    )
    return PaginatedResponse(
        items=[UserResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.read"))],
)
async def get_user(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> UserResponse:
    return UserResponse.model_validate(await UserService(unit_of_work).get(user_id))


@router.patch(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def update_user(
    user_id: UUID, payload: UserUpdate, unit_of_work: UnitOfWorkDependency
) -> UserResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return UserResponse.model_validate(
        await UserService(unit_of_work).update(user_id, data, version)
    )


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def delete_user(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> Response:
    await UserService(unit_of_work).soft_delete(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def activate_user(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> UserResponse:
    return UserResponse.model_validate(await UserService(unit_of_work).set_active(user_id, True))


@router.post(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def deactivate_user(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> UserResponse:
    return UserResponse.model_validate(await UserService(unit_of_work).set_active(user_id, False))


@router.post(
    "/users/{user_id}/unlock",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def unlock_user(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> UserResponse:
    return UserResponse.model_validate(await UserService(unit_of_work).unlock(user_id))


@router.post(
    "/users/{user_id}/reset-password",
    response_model=PasswordResetResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def reset_password(
    user_id: UUID, unit_of_work: UnitOfWorkDependency
) -> PasswordResetResponse:
    return PasswordResetResponse(
        temporary_password=await UserService(unit_of_work).reset_password(user_id)
    )


@router.put(
    "/users/{user_id}/roles",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def set_user_roles(
    user_id: UUID, payload: RoleAssignmentRequest, unit_of_work: UnitOfWorkDependency
) -> UserResponse:
    return UserResponse.model_validate(
        await UserService(unit_of_work).set_roles(user_id, payload.role_ids)
    )


@router.get(
    "/users/{user_id}/sessions",
    response_model=list[SessionResponse],
    dependencies=[Depends(require_permission("sessions.manage"))],
)
async def user_sessions(user_id: UUID, unit_of_work: UnitOfWorkDependency) -> list[SessionResponse]:
    sessions = await SessionRepository(unit_of_work._session).list_for_user(user_id)
    return [SessionResponse.model_validate(session) for session in sessions]


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("sessions.manage"))],
)
async def revoke_user_session(
    user_id: UUID, session_id: UUID, unit_of_work: UnitOfWorkDependency
) -> Response:
    session = await SessionRepository(unit_of_work._session).get(session_id)
    if session is None or session.user_id != user_id:
        raise PermissionDeniedError("Session is not active.")
    await AuthService(unit_of_work).logout(session_id, "administrator revoke")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("roles.manage"))],
)
async def create_role(payload: RoleCreate, unit_of_work: UnitOfWorkDependency) -> RoleResponse:
    return RoleResponse.model_validate(await RoleService(unit_of_work).create(payload.model_dump()))


@router.get(
    "/roles",
    response_model=PaginatedResponse[RoleResponse],
    dependencies=[Depends(require_permission("roles.read"))],
)
async def list_roles(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    sort_by: str = "name",
    sort_direction: SortDirection = SortDirection.ASC,
    search: str | None = None,
) -> PaginatedResponse[RoleResponse]:
    page_request = PageRequest(page=page, page_size=page_size)
    items, total = await RoleService(unit_of_work).list(
        {"search": search}, page_request, sort_by, sort_direction
    )
    return PaginatedResponse(
        items=[RoleResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.read"))],
)
async def get_role(role_id: UUID, unit_of_work: UnitOfWorkDependency) -> RoleResponse:
    return RoleResponse.model_validate(await RoleService(unit_of_work).get(role_id))


@router.patch(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.manage"))],
)
async def update_role(
    role_id: UUID, payload: RoleUpdate, unit_of_work: UnitOfWorkDependency
) -> RoleResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return RoleResponse.model_validate(
        await RoleService(unit_of_work).update(role_id, data, version)
    )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("roles.manage"))],
)
async def delete_role(role_id: UUID, unit_of_work: UnitOfWorkDependency) -> Response:
    await RoleService(unit_of_work).soft_delete(role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/roles/{role_id}/permissions",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("roles.manage"))],
)
async def set_role_permissions(
    role_id: UUID, payload: PermissionAssignmentRequest, unit_of_work: UnitOfWorkDependency
) -> RoleResponse:
    return RoleResponse.model_validate(
        await RoleService(unit_of_work).set_permissions(role_id, payload.permission_ids)
    )


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission("roles.read"))],
)
async def list_permissions(unit_of_work: UnitOfWorkDependency) -> list[PermissionResponse]:
    permissions = await PermissionRepository(unit_of_work._session).list()
    return [PermissionResponse.model_validate(permission) for permission in permissions]


@router.post("/identity/bootstrap", status_code=status.HTTP_204_NO_CONTENT)
async def bootstrap_identity(unit_of_work: UnitOfWorkDependency) -> Response:
    await IdentityService(unit_of_work).bootstrap_admin()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _set_auth_cookies(response: Response, refresh_token: str, session_id: str) -> None:
    same_site = cast(Literal["lax", "strict", "none"], settings.auth_cookie_samesite)
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=same_site,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
    )
    response.set_cookie(
        "session_id",
        session_id,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=same_site,
        max_age=settings.auth_refresh_token_days * 24 * 60 * 60,
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("refresh_token")
    response.delete_cookie("session_id")
