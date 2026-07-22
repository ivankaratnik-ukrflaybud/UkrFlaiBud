from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services import (
    CncMaterialService,
    CncOutputService,
    CncQueryService,
    CncQueueService,
    CncWorkOrderService,
)
from app.modules.cnc.infrastructure.repositories import CncMaterialTransactionRepository
from app.modules.cnc.presentation.schemas import (
    ChangeMachinePayload,
    CncOffcutResponse,
    CncOutputResponse,
    CncWorkOrderCreate,
    CncWorkOrderResponse,
    CncWorkOrderUpdate,
    MaterialPayload,
    MaterialTransactionResponse,
    RegisterOffcutPayload,
    ReorderPayload,
    ReportOutputPayload,
)
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter()


@router.get(
    "/work-orders",
    response_model=PaginatedResponse[CncWorkOrderResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def list_work_orders(
    organization_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    priority: str | None = None,
    machine_id: UUID | None = None,
    site_id: UUID | None = None,
    production_order_id: UUID | None = None,
    material_item_id: UUID | None = None,
    cnc_part_id: UUID | None = None,
    operator_employee_id: UUID | None = None,
    blocked: bool | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_direction: SortDirection = SortDirection.DESC,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    items, total = await CncWorkOrderService(unit_of_work).list_orders(
        filters={
            "organization_id": organization_id,
            "status": status_filter,
            "priority": priority,
            "machine_id": machine_id,
            "site_id": site_id,
            "production_order_id": production_order_id,
            "material_item_id": material_item_id,
            "cnc_part_id": cnc_part_id,
            "operator_employee_id": operator_employee_id,
            "blocked": blocked,
            "search": search,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return PaginatedResponse[CncWorkOrderResponse](
        items=[CncWorkOrderResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/work-orders",
    response_model=CncWorkOrderResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("cnc.work_orders.create"))],
)
async def create_work_order(
    payload: CncWorkOrderCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncWorkOrderService(unit_of_work).create(
            payload.model_dump(exclude_none=True), actor_id=user_id, user=user
        )
    )


@router.get(
    "/work-orders/{work_order_id}",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def get_work_order(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncWorkOrderService(unit_of_work).get(work_order_id, user=user)
    )


@router.patch(
    "/work-orders/{work_order_id}",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.edit"))],
)
async def update_work_order(
    work_order_id: UUID,
    payload: CncWorkOrderUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version", None)
    return CncWorkOrderResponse.model_validate(
        await CncWorkOrderService(unit_of_work).update(
            work_order_id, data, expected_version=expected_version, actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/plan",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.plan"))],
)
async def plan_work_order(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncWorkOrderService(unit_of_work).transition(
            work_order_id, "planned", actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/queue",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.queue"))],
)
async def queue_work_order(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncQueueService(unit_of_work).queue(work_order_id, actor_id=user_id, user=user)
    )


@router.get(
    "/queue",
    response_model=PaginatedResponse[CncWorkOrderResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    organization_id: UUID | None = None,
    machine_id: UUID | None = None,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    items, total = await CncQueueService(unit_of_work).list_queue(
        filters={"organization_id": organization_id, "machine_id": machine_id},
        page=PageRequest(page=page, page_size=page_size),
        user=user,
    )
    return PaginatedResponse[CncWorkOrderResponse](
        items=[CncWorkOrderResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/queue/reorder",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("cnc.work_orders.queue"))],
)
async def reorder_queue(
    payload: ReorderPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    await CncQueueService(unit_of_work).reorder(
        payload.machine_id, payload.ordered_work_order_ids, actor_id=user_id, user=user
    )


@router.post(
    "/work-orders/{work_order_id}/change-machine",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.queue"))],
)
async def change_machine(
    work_order_id: UUID,
    payload: ChangeMachinePayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncQueueService(unit_of_work).change_machine(
            work_order_id, payload.machine_id, actor_id=user_id, user=user
        )
    )


@router.get(
    "/work-orders/{work_order_id}/material",
    response_model=list[MaterialTransactionResponse],
    dependencies=[Depends(require_permission("cnc.materials.read"))],
)
async def material_transactions(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
):
    work_order = await CncWorkOrderService(unit_of_work).get(work_order_id, user=user)
    if unit_of_work.session is None:
        raise RuntimeError("Unit of Work session is not active.")
    return [
        MaterialTransactionResponse.model_validate(item)
        for item in await CncMaterialTransactionRepository(
            unit_of_work.session
        ).list_for_work_order(work_order.id)
    ]


@router.post(
    "/work-orders/{work_order_id}/material-issue",
    response_model=MaterialTransactionResponse,
    dependencies=[Depends(require_permission("cnc.materials.issue"))],
)
async def material_issue(
    work_order_id: UUID,
    payload: MaterialPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return MaterialTransactionResponse.model_validate(
        await CncMaterialService(unit_of_work).issue(
            work_order_id, payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/material-return",
    response_model=MaterialTransactionResponse,
    dependencies=[Depends(require_permission("cnc.materials.return"))],
)
async def material_return(
    work_order_id: UUID,
    payload: MaterialPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return MaterialTransactionResponse.model_validate(
        await CncMaterialService(unit_of_work).return_material(
            work_order_id, payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/material-scrap",
    response_model=MaterialTransactionResponse,
    dependencies=[Depends(require_permission("cnc.materials.scrap"))],
)
async def material_scrap(
    work_order_id: UUID,
    payload: MaterialPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return MaterialTransactionResponse.model_validate(
        await CncMaterialService(unit_of_work).scrap(
            work_order_id, payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.get(
    "/work-orders/{work_order_id}/outputs",
    response_model=list[CncOutputResponse],
    dependencies=[Depends(require_permission("cnc.read"))],
)
async def outputs(
    work_order_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    return [
        CncOutputResponse.model_validate(item)
        for item in await CncOutputService(unit_of_work).outputs(work_order_id)
    ]


@router.post(
    "/work-orders/{work_order_id}/report-output",
    response_model=CncWorkOrderResponse,
    dependencies=[Depends(require_permission("cnc.work_orders.complete"))],
)
async def report_output(
    work_order_id: UUID,
    payload: ReportOutputPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncWorkOrderResponse.model_validate(
        await CncOutputService(unit_of_work).report_output(
            work_order_id, payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/receipt-output",
    response_model=CncOutputResponse,
    dependencies=[Depends(require_permission("cnc.output.post"))],
)
async def receipt_output(
    work_order_id: UUID,
    output_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncOutputResponse.model_validate(
        await CncOutputService(unit_of_work).receipt_output(
            work_order_id, output_id, actor_id=user_id, user=user
        )
    )


@router.post(
    "/work-orders/{work_order_id}/register-offcut",
    response_model=CncOffcutResponse,
    dependencies=[Depends(require_permission("cnc.offcuts.manage"))],
)
async def register_offcut(
    work_order_id: UUID,
    payload: RegisterOffcutPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
):
    return CncOffcutResponse.model_validate(
        await CncOutputService(unit_of_work).register_offcut(
            work_order_id, payload.model_dump(), actor_id=user_id, user=user
        )
    )


@router.get(
    "/work-orders/{work_order_id}/readiness", dependencies=[Depends(require_permission("cnc.read"))]
)
async def readiness(
    work_order_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    return await CncQueryService(unit_of_work).readiness(work_order_id)
