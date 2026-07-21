from __future__ import annotations

# ruff: noqa: B008
from collections.abc import Sequence
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.api.dependencies import get_unit_of_work
from app.database.audit import AuditAction
from app.modules.bom.application.documents import (
    export_filename,
    render_import_template,
    render_pdf,
    render_preview_html,
    render_xlsx,
)
from app.modules.bom.application.services import BomService
from app.modules.bom.presentation.schemas import (
    AttachmentCreate,
    AttachmentResponse,
    ImportPreviewResponse,
    ImportResultResponse,
    LineCreate,
    LineResponse,
    LineUpdate,
    ReorderPayload,
    SpecificationCopyPayload,
    SpecificationCreate,
    SpecificationResponse,
    SpecificationUpdate,
    VersionCompareResponse,
    VersionCreate,
    VersionResponse,
    VersionUpdate,
)
from app.modules.identity.presentation.dependencies import current_user_id, require_permission
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, PaginatedResponse, SortDirection

router = APIRouter(prefix="/bom")


def _page(
    items: Sequence[object], total: int, page: int, page_size: int, model: type[BaseModel]
) -> PaginatedResponse[Any]:
    return PaginatedResponse[Any](
        items=[model.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/specifications",
    response_model=SpecificationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bom.create"))],
)
async def create_specification(
    payload: SpecificationCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> SpecificationResponse:
    return SpecificationResponse.model_validate(
        await BomService(unit_of_work).create_specification(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/specifications",
    response_model=PaginatedResponse[SpecificationResponse],
    dependencies=[Depends(require_permission("bom.read"))],
)
async def list_specifications(
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_direction: SortDirection = SortDirection.DESC,
    organization_id: UUID | None = None,
    product_item_id: UUID | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[SpecificationResponse]:
    items, total = await BomService(unit_of_work).list_specifications(
        filters={
            "organization_id": organization_id,
            "product_item_id": product_item_id,
            "status": status_filter,
            "search": search,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, SpecificationResponse)


@router.get(
    "/specifications/{specification_id}",
    response_model=SpecificationResponse,
    dependencies=[Depends(require_permission("bom.read"))],
)
async def get_specification(
    specification_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
) -> SpecificationResponse:
    return SpecificationResponse.model_validate(
        await BomService(unit_of_work).get_specification(specification_id)
    )


@router.patch(
    "/specifications/{specification_id}",
    response_model=SpecificationResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def update_specification(
    specification_id: UUID,
    payload: SpecificationUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> SpecificationResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return SpecificationResponse.model_validate(
        await BomService(unit_of_work).update_specification(
            specification_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/specifications/{specification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def delete_specification(
    specification_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> Response:
    await BomService(unit_of_work).archive_specification(specification_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/specifications/{specification_id}/archive",
    response_model=SpecificationResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def archive_specification(
    specification_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> SpecificationResponse:
    return SpecificationResponse.model_validate(
        await BomService(unit_of_work).archive_specification(specification_id, actor_id=user_id)
    )


@router.post(
    "/specifications/{specification_id}/copy",
    response_model=SpecificationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bom.create"))],
)
async def copy_specification(
    specification_id: UUID,
    payload: SpecificationCopyPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> SpecificationResponse:
    return SpecificationResponse.model_validate(
        await BomService(unit_of_work).copy_specification(
            specification_id, payload.model_dump(), actor_id=user_id
        )
    )


@router.get(
    "/specifications/{specification_id}/versions",
    response_model=list[VersionResponse],
    dependencies=[Depends(require_permission("bom.read"))],
)
async def list_versions(
    specification_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
) -> list[VersionResponse]:
    return [
        VersionResponse.model_validate(version)
        for version in await BomService(unit_of_work).list_versions(specification_id)
    ]


@router.post(
    "/specifications/{specification_id}/versions",
    response_model=VersionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bom.create"))],
)
async def create_version(
    specification_id: UUID,
    payload: VersionCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).create_version(
            specification_id, payload.model_dump(exclude_unset=True), actor_id=user_id
        )
    )


@router.get(
    "/versions/{version_id}",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.read"))],
)
async def get_version(
    version_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
) -> VersionResponse:
    return VersionResponse.model_validate(await BomService(unit_of_work).get_version(version_id))


@router.patch(
    "/versions/{version_id}",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def update_version(
    version_id: UUID,
    payload: VersionUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return VersionResponse.model_validate(
        await BomService(unit_of_work).update_version(
            version_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.post(
    "/versions/{version_id}/submit-review",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def submit_review(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).submit_review(version_id, actor_id=user_id)
    )


@router.post(
    "/versions/{version_id}/approve",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.approve"))],
)
async def approve_version(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).approve_version(version_id, actor_id=user_id)
    )


@router.post(
    "/versions/{version_id}/supersede",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.approve"))],
)
async def supersede_version(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).supersede_version(version_id, actor_id=user_id)
    )


@router.post(
    "/versions/{version_id}/archive",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.approve"))],
)
async def archive_version(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).archive_version(version_id, actor_id=user_id)
    )


@router.post(
    "/versions/{version_id}/copy",
    response_model=VersionResponse,
    dependencies=[Depends(require_permission("bom.create"))],
)
async def copy_version(
    version_id: UUID,
    payload: VersionCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> VersionResponse:
    return VersionResponse.model_validate(
        await BomService(unit_of_work).copy_version(
            version_id, payload.model_dump(exclude_unset=True), actor_id=user_id
        )
    )


@router.get(
    "/versions/{version_id}/lines",
    response_model=list[LineResponse],
    dependencies=[Depends(require_permission("bom.read"))],
)
async def list_lines(
    version_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
) -> list[LineResponse]:
    return [
        LineResponse.model_validate(line)
        for line in await BomService(unit_of_work).list_lines(version_id)
    ]


@router.post(
    "/versions/{version_id}/lines",
    response_model=LineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def add_line(
    version_id: UUID,
    payload: LineCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> LineResponse:
    return LineResponse.model_validate(
        await BomService(unit_of_work).add_line(
            version_id, payload.model_dump(exclude_unset=True), actor_id=user_id
        )
    )


@router.patch(
    "/versions/{version_id}/lines/{line_id}",
    response_model=LineResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def update_line(
    version_id: UUID,
    line_id: UUID,
    payload: LineUpdate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> LineResponse:
    data = payload.model_dump(exclude_unset=True)
    expected_version = data.pop("version")
    return LineResponse.model_validate(
        await BomService(unit_of_work).update_line(
            version_id, line_id, data, expected_version=expected_version, actor_id=user_id
        )
    )


@router.delete(
    "/versions/{version_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def delete_line(
    version_id: UUID,
    line_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> Response:
    await BomService(unit_of_work).delete_line(version_id, line_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/versions/{version_id}/lines/reorder",
    response_model=list[LineResponse],
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def reorder_lines(
    version_id: UUID,
    payload: ReorderPayload,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> list[LineResponse]:
    return [
        LineResponse.model_validate(line)
        for line in await BomService(unit_of_work).reorder_lines(
            version_id, payload.line_ids, actor_id=user_id
        )
    ]


@router.post(
    "/versions/{version_id}/lines/{line_id}/duplicate",
    response_model=LineResponse,
    dependencies=[Depends(require_permission("bom.edit"))],
)
async def duplicate_line(
    version_id: UUID,
    line_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> LineResponse:
    return LineResponse.model_validate(
        await BomService(unit_of_work).duplicate_line(version_id, line_id, actor_id=user_id)
    )


@router.get(
    "/versions/{version_id}/preview",
    response_class=HTMLResponse,
    dependencies=[Depends(require_permission("bom.read"))],
)
async def preview_version(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    toolbar: bool = Query(default=True),
) -> HTMLResponse:
    document = await BomService(unit_of_work).prepare_document(version_id)
    return HTMLResponse(render_preview_html(document, include_toolbar=toolbar))


@router.get(
    "/versions/{version_id}/export/pdf",
    dependencies=[Depends(require_permission("bom.export"))],
)
async def export_pdf(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> Response:
    service = BomService(unit_of_work)
    document = await service.prepare_document(version_id)
    content = render_pdf(document)
    filename = export_filename(
        document["specification"]["code"], document["version"]["version_number"], "pdf"
    )
    await service._audit(  # noqa: SLF001
        action=AuditAction.EXPORT_PDF.value,
        entity_type="bom_version",
        entity_id=version_id,
        actor_id=user_id,
        after={"filename": filename},
    )
    await unit_of_work.commit()
    return Response(
        content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/versions/{version_id}/export/xlsx",
    dependencies=[Depends(require_permission("bom.export"))],
)
async def export_xlsx(
    version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> Response:
    service = BomService(unit_of_work)
    document = await service.prepare_document(version_id)
    content = render_xlsx(document)
    filename = export_filename(
        document["specification"]["code"], document["version"]["version_number"], "xlsx"
    )
    await service._audit(  # noqa: SLF001
        action=AuditAction.EXPORT_XLSX.value,
        entity_type="bom_version",
        entity_id=version_id,
        actor_id=user_id,
        after={"filename": filename},
    )
    await unit_of_work.commit()
    return Response(
        content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/import/template",
    dependencies=[Depends(require_permission("bom.import"))],
)
async def import_template() -> Response:
    return Response(
        render_import_template(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="BOM_import_template.xlsx"'},
    )


@router.post(
    "/versions/{version_id}/import/xlsx",
    response_model=ImportPreviewResponse | ImportResultResponse,
    dependencies=[Depends(require_permission("bom.import"))],
)
async def import_xlsx(
    version_id: UUID,
    file: UploadFile = File(...),
    confirm: bool = Query(False),
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> ImportPreviewResponse | ImportResultResponse:
    content = await file.read()
    service = BomService(unit_of_work)
    if confirm:
        return ImportResultResponse.model_validate(
            await service.import_lines(version_id, content, actor_id=user_id)
        )
    return ImportPreviewResponse.model_validate(await service.validate_import(version_id, content))


@router.get(
    "/versions/{version_id}/attachments",
    response_model=list[AttachmentResponse],
    dependencies=[Depends(require_permission("bom.read"))],
)
async def list_attachments(
    version_id: UUID, unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work)
) -> list[AttachmentResponse]:
    return [
        AttachmentResponse.model_validate(attachment)
        for attachment in await BomService(unit_of_work).list_attachments(version_id)
    ]


@router.post(
    "/versions/{version_id}/attachments",
    response_model=AttachmentResponse,
    dependencies=[Depends(require_permission("bom.attachments"))],
)
async def add_attachment(
    version_id: UUID,
    payload: AttachmentCreate,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> AttachmentResponse:
    return AttachmentResponse.model_validate(
        await BomService(unit_of_work).add_attachment(
            version_id, payload.model_dump(), actor_id=user_id
        )
    )


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("bom.attachments"))],
)
async def delete_attachment(
    attachment_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
    user_id: UUID = Depends(current_user_id),
) -> Response:
    await BomService(unit_of_work).delete_attachment(attachment_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/versions/{left_version_id}/compare/{right_version_id}",
    response_model=VersionCompareResponse,
    dependencies=[Depends(require_permission("bom.read"))],
)
async def compare_versions(
    left_version_id: UUID,
    right_version_id: UUID,
    unit_of_work: SQLAlchemyUnitOfWork = Depends(get_unit_of_work),
) -> VersionCompareResponse:
    service = BomService(unit_of_work)
    left = await service.prepare_document(left_version_id)
    right = await service.prepare_document(right_version_id)
    left_lines = {line["line_number"]: line for line in left["lines"]}
    right_lines = {line["line_number"]: line for line in right["lines"]}
    added = [right_lines[number] for number in sorted(set(right_lines) - set(left_lines))]
    removed = [left_lines[number] for number in sorted(set(left_lines) - set(right_lines))]
    changed = []
    for number in sorted(set(left_lines) & set(right_lines)):
        before = left_lines[number]
        after = right_lines[number]
        fields = ["display_name", "quantity", "unit_symbol", "notes"]
        changes = {
            field: {"before": before.get(field), "after": after.get(field)}
            for field in fields
            if before.get(field) != after.get(field)
        }
        if changes:
            changed.append({"line_number": number, "changes": changes})
    return VersionCompareResponse(added=added, removed=removed, changed=changed)
