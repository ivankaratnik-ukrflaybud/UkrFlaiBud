from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import CncExecutionService
from app.modules.cnc.presentation.schemas import CncWorkOrderResponse, StatusPayload
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

router = APIRouter()


@router.post(
    "/work-orders/{work_order_id}/start-setup",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.start"))],
)
async def start_setup(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).start_setup(
            work_order_id, actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/start",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.start"))],
)
async def start(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).start(work_order_id, actor_id=user_id, user=user)
    )


@router.post(
    "/work-orders/{work_order_id}/pause",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.pause"))],
)
async def pause(
    work_order_id: UUID,
    payload: StatusPayload | None = None,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).pause(
            work_order_id, actor_id=user_id, user=user, reason=payload.reason if payload else None
        )
    )


@router.post(
    "/work-orders/{work_order_id}/resume",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.start"))],
)
async def resume(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).resume(work_order_id, actor_id=user_id, user=user)
    )


@router.post(
    "/work-orders/{work_order_id}/block",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.queue"))],
)
async def block(
    work_order_id: UUID,
    payload: StatusPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).block(
            work_order_id, actor_id=user_id, user=user, reason=payload.reason
        )
    )


@router.post(
    "/work-orders/{work_order_id}/unblock",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.queue"))],
)
async def unblock(
    work_order_id: UUID,
    payload: StatusPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).unblock(
            work_order_id, payload.status, actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/cancel",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.cancel"))],
)
async def cancel(
    work_order_id: UUID,
    payload: StatusPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).cancel(
            work_order_id, actor_id=user_id, user=user, reason=payload.reason
        )
    )


@router.post(
    "/work-orders/{work_order_id}/complete",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.complete"))],
)
async def complete(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncExecutionService(unit_of_work).complete(work_order_id, actor_id=user_id, user=user)
    )
