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
from app.modules.production.application.services import (
    ConsumptionService,
    MaterialIssueService,
    MaterialReturnService,
    RequirementService,
    ReservationService,
)
from app.modules.production.domain.entities import ProductionMaterialTransactionType
from app.modules.production.presentation.schemas import (
    MaterialOperationPayload,
    RequirementAvailabilityResponse,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

router = APIRouter()


@router.get(
    "/orders/{order_id}/materials",
    response_model=list[RequirementAvailabilityResponse],
    dependencies=[Depends(require_permission("production.read"))],
)
async def list_materials(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
) -> list[RequirementAvailabilityResponse]:
    return [
        RequirementAvailabilityResponse.model_validate(item)
        for item in await RequirementService(unit_of_work).list_requirements(order_id, user=user)
    ]


@router.post(
    "/orders/{order_id}/reserve-materials",
    dependencies=[Depends(require_permission("production.reserve"))],
)
async def reserve_materials(
    order_id: UUID,
    payload: MaterialOperationPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> dict[str, int]:
    reservations = await ReservationService(unit_of_work).reserve(
        order_id,
        [line.model_dump(exclude_unset=True) for line in payload.lines] or None,
        actor_id=user_id,
        user=user,
    )
    return {"reserved_lines": len(reservations)}


@router.post(
    "/orders/{order_id}/release-reservations",
    dependencies=[Depends(require_permission("production.reserve"))],
)
async def release_reservations(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> dict[str, bool]:
    await ReservationService(unit_of_work).release_all(order_id, actor_id=user_id)
    await unit_of_work.commit()
    return {"released": True}


@router.post(
    "/orders/{order_id}/issue-materials",
    dependencies=[Depends(require_permission("production.issue"))],
)
async def issue_materials(
    order_id: UUID,
    payload: MaterialOperationPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> dict[str, str]:
    transaction = await MaterialIssueService(unit_of_work).issue(
        order_id,
        [line.model_dump(exclude_unset=True) for line in payload.lines],
        actor_id=user_id,
        user=user,
        allow_overissue=payload.allow_overissue,
        reason=payload.reason,
        notes=payload.notes,
    )
    return {"transaction_id": str(transaction.id)}


@router.post(
    "/orders/{order_id}/return-materials",
    dependencies=[Depends(require_permission("production.issue"))],
)
async def return_materials(
    order_id: UUID,
    payload: MaterialOperationPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> dict[str, str]:
    transaction = await MaterialReturnService(unit_of_work).return_materials(
        order_id,
        [line.model_dump(exclude_unset=True) for line in payload.lines],
        actor_id=user_id,
        user=user,
        notes=payload.notes,
    )
    return {"transaction_id": str(transaction.id)}


@router.post(
    "/orders/{order_id}/consume-materials",
    dependencies=[Depends(require_permission("production.consume"))],
)
async def consume_materials(
    order_id: UUID,
    payload: MaterialOperationPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> dict[str, str]:
    transaction = await ConsumptionService(unit_of_work).record(
        order_id,
        [line.model_dump(exclude_unset=True) for line in payload.lines],
        transaction_type=ProductionMaterialTransactionType.CONSUMPTION.value,
        actor_id=user_id,
        reason=payload.reason,
    )
    return {"transaction_id": str(transaction.id)}


@router.post(
    "/orders/{order_id}/scrap-materials",
    dependencies=[Depends(require_permission("production.consume"))],
)
async def scrap_materials(
    order_id: UUID,
    payload: MaterialOperationPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> dict[str, str]:
    transaction = await ConsumptionService(unit_of_work).record(
        order_id,
        [line.model_dump(exclude_unset=True) for line in payload.lines],
        transaction_type=ProductionMaterialTransactionType.SCRAP.value,
        actor_id=user_id,
        reason=payload.reason,
    )
    return {"transaction_id": str(transaction.id)}
