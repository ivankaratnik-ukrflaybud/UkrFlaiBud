from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_unit_of_work
from app.modules.identity.infrastructure.models import UserModel
from app.modules.identity.presentation.dependencies import (
    current_user,
    current_user_id,
    require_permission,
)
from app.modules.production.application.services.documents import (
    ProductionDocumentService,
    export_filename,
    render_pdf,
    render_preview_html,
    render_xlsx,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

router = APIRouter()


@router.get(
    "/orders/{order_id}/preview",
    response_class=HTMLResponse,
    dependencies=[Depends(require_permission("production.read"))],
)
async def preview_order(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user: UserModel = Depends(current_user),
    toolbar: bool = Query(default=True),
) -> HTMLResponse:
    document = await ProductionDocumentService(unit_of_work).prepare_document(order_id, user=user)
    return HTMLResponse(render_preview_html(document, include_toolbar=toolbar))


@router.get(
    "/orders/{order_id}/export/pdf",
    dependencies=[Depends(require_permission("production.export"))],
)
async def export_pdf(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> Response:
    service = ProductionDocumentService(unit_of_work)
    document = await service.prepare_document(order_id, user=user)
    content = render_pdf(document)
    await service.audit_export(order_id, suffix="pdf", actor_id=user_id)
    await unit_of_work.commit()
    filename = export_filename(document["order"]["order_number"], "pdf")
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/orders/{order_id}/export/xlsx",
    dependencies=[Depends(require_permission("production.export"))],
)
async def export_xlsx(
    order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
    user: UserModel = Depends(current_user),
) -> Response:
    service = ProductionDocumentService(unit_of_work)
    document = await service.prepare_document(order_id, user=user)
    content = render_xlsx(document)
    await service.audit_export(order_id, suffix="xlsx", actor_id=user_id)
    await unit_of_work.commit()
    filename = export_filename(document["order"]["order_number"], "xlsx")
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
