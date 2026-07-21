from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_unit_of_work
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.modules.production.application.services import CompletionService, SerialRegistrationService
from app.modules.production.presentation.schemas import CompletionCreate, CompletionResponse
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

router = APIRouter()


@router.post(
    "/orders/{order_id}/complete",
    response_model=CompletionResponse,
    dependencies=[Depends(require_permission("production.complete"))],
)
async def complete_order(
    order_id: UUID,
    payload: CompletionCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> CompletionResponse:
    return CompletionResponse.model_validate(
        await CompletionService(unit_of_work).complete(
            order_id, payload.model_dump(exclude_unset=True), actor_id=user_id, user=user
        )
    )


@router.get(
    "/orders/{order_id}/serials",
    dependencies=[Depends(require_permission("production.read"))],
)
async def output_serials(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
) -> list[dict[str, str]]:
    serials = await SerialRegistrationService(unit_of_work).list_for_order(order_id, user=user)
    return [
        {
            "id": str(serial.id),
            "serial_number": serial.serial_number_snapshot,
            "completion_id": str(serial.completion_id),
        }
        for serial in serials
    ]
