from collections.abc import Callable
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Header

from app.api.dependencies import get_unit_of_work
from app.models.base import PermissionDeniedError
from app.modules.identity.application.security import decode_access_token
from app.modules.identity.application.services import UserService, require_permission_for_user
from app.modules.identity.infrastructure.models import UserModel
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork


async def current_user_id(authorization: Annotated[str | None, Header()] = None) -> UUID:
    if not authorization or not authorization.startswith("Bearer "):
        raise PermissionDeniedError("Authentication required.")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise PermissionDeniedError("Authentication required.") from exc
    return UUID(payload["sub"])


async def current_user(
    user_id: Annotated[UUID, Depends(current_user_id)],
    unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
) -> UserModel:
    return await UserService(unit_of_work).get(user_id)


def require_permission(permission_code: str) -> Callable[..., object]:
    async def dependency(
        user_id: Annotated[UUID, Depends(current_user_id)],
        unit_of_work: Annotated[SQLAlchemyUnitOfWork, Depends(get_unit_of_work)],
    ) -> None:
        await require_permission_for_user(unit_of_work, user_id, permission_code)

    return dependency
