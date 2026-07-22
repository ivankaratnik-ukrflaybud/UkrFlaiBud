from __future__ import annotations

# ruff: noqa: B008
from uuid import UUID

from fastapi import APIRouter, Depends, Response

from app.api.dependencies import get_unit_of_work
from app.modules.cnc.application.services.documents import CncDocumentService
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork

router = APIRouter()


@router.get(
    "/work-orders/{work_order_id}/preview", dependencies=[Depends(require_permission("cnc.export"))]
)
async def preview(
    work_order_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
):
    html = await CncDocumentService(unit_of_work).preview_html(work_order_id)
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"X-CNC-Printed-By": str(user_id)},
    )


@router.get(
    "/work-orders/{work_order_id}/export/pdf",
    dependencies=[Depends(require_permission("cnc.export"))],
)
async def export_pdf(
    work_order_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    content = await CncDocumentService(unit_of_work).pdf(work_order_id)
    filename = f"cnc-work-order-{work_order_id}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/work-orders/{work_order_id}/export/xlsx",
    dependencies=[Depends(require_permission("cnc.export"))],
)
async def export_xlsx(
    work_order_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
):
    content = await CncDocumentService(unit_of_work).xlsx(work_order_id)
    filename = f"cnc-work-order-{work_order_id}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
