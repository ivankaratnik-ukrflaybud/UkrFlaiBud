# ruff: noqa: F401,I001
from .common import (
    Sequence,
    Annotated,
    Any,
    UUID,
    APIRouter,
    Depends,
    Query,
    Response,
    status,
    get_unit_of_work,
    UserModel,
    current_user,
    current_user_id,
    require_permission,
    CatalogService,
    DocumentService,
    InventoryScopeService,
    LocationService,
    SiteService,
    StockService,
    TrackingService,
    WarehouseService,
    InventoryDocumentStatus,
    InventoryDocumentType,
    ItemType,
    SerialStatus,
    AttachSerialsPayload,
    CancelDocumentPayload,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    DocumentCreate,
    DocumentLineCreate,
    DocumentLineResponse,
    DocumentLineUpdate,
    DocumentResponse,
    DocumentUpdate,
    ItemCreate,
    ItemResponse,
    ItemUpdate,
    LocationCreate,
    LocationResponse,
    LocationUpdate,
    LotCreate,
    LotResponse,
    MovementResponse,
    SerialCreate,
    SerialResponse,
    SerialStatusUpdate,
    SiteCreate,
    SiteResponse,
    SiteUpdate,
    StockBalanceResponse,
    UnitCreate,
    UnitResponse,
    UnitUpdate,
    UserInventoryScopeResponse,
    UserInventoryScopeUpdate,
    WarehouseCreate,
    WarehouseResponse,
    WarehouseUpdate,
    SQLAlchemyUnitOfWork,
    PageRequest,
    PaginatedResponse,
    SortDirection,
    router,
    identity_scope_router,
    UnitOfWorkDependency,
    CurrentUserDependency,
    CurrentUserIdDependency,
    SortDirectionQuery,
    SerialStatusQuery,
    DocumentStatusQuery,
    _page,
)


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.documents.create"))],
)
async def create_document(
    payload: DocumentCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> DocumentResponse:
    data = payload.model_dump(exclude_none=True)
    return DocumentResponse.model_validate(
        await DocumentService(unit_of_work).create_draft(data, actor_id=user_id)
    )


@router.get(
    "/documents",
    response_model=PaginatedResponse[DocumentResponse],
    dependencies=[Depends(require_permission("inventory.documents.read"))],
)
async def list_documents(
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "document_date",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    document_type: InventoryDocumentType | None = None,
    status_filter: DocumentStatusQuery = None,
) -> PaginatedResponse[DocumentResponse]:
    items, total = await DocumentService(unit_of_work).list_documents(
        filters={
            "organization_id": organization_id,
            "document_type": document_type,
            "status": status_filter,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, DocumentResponse)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("inventory.documents.read"))],
)
async def get_document(document_id: UUID, unit_of_work: UnitOfWorkDependency) -> DocumentResponse:
    return DocumentResponse.model_validate(await DocumentService(unit_of_work).get(document_id))


@router.patch(
    "/documents/{document_id}",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("inventory.documents.edit"))],
)
async def update_document(
    document_id: UUID,
    payload: DocumentUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> DocumentResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return DocumentResponse.model_validate(
        await DocumentService(unit_of_work).update_header(
            document_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.get(
    "/documents/{document_id}/lines",
    response_model=list[DocumentLineResponse],
    dependencies=[Depends(require_permission("inventory.documents.read"))],
)
async def list_document_lines(
    document_id: UUID, unit_of_work: UnitOfWorkDependency
) -> list[DocumentLineResponse]:
    return [
        DocumentLineResponse.model_validate(line)
        for line in await DocumentService(unit_of_work).lines(document_id)
    ]


@router.post(
    "/documents/{document_id}/lines",
    response_model=DocumentLineResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.documents.edit"))],
)
async def add_document_line(
    document_id: UUID,
    payload: DocumentLineCreate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> DocumentLineResponse:
    return DocumentLineResponse.model_validate(
        await DocumentService(unit_of_work).add_line(
            document_id, payload.model_dump(), actor_id=user_id
        )
    )


@router.patch(
    "/documents/{document_id}/lines/{line_id}",
    response_model=DocumentLineResponse,
    dependencies=[Depends(require_permission("inventory.documents.edit"))],
)
async def update_document_line(
    document_id: UUID,
    line_id: UUID,
    payload: DocumentLineUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> DocumentLineResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return DocumentLineResponse.model_validate(
        await DocumentService(unit_of_work).update_line(
            document_id, line_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/documents/{document_id}/lines/{line_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.documents.edit"))],
)
async def delete_document_line(
    document_id: UUID,
    line_id: UUID,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> Response:
    await DocumentService(unit_of_work).delete_line(document_id, line_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/lines/{line_id}/serials",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.documents.edit"))],
)
async def attach_document_line_serials(
    document_id: UUID,
    line_id: UUID,
    payload: AttachSerialsPayload,
    unit_of_work: UnitOfWorkDependency,
) -> Response:
    await DocumentService(unit_of_work).attach_serials(document_id, line_id, payload.serial_ids)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/documents/{document_id}/post",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("inventory.documents.post"))],
)
async def post_document(
    document_id: UUID,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
    user: CurrentUserDependency,
) -> DocumentResponse:
    return DocumentResponse.model_validate(
        await DocumentService(unit_of_work).post(document_id, actor_id=user_id, user=user)
    )


@router.post(
    "/documents/{document_id}/cancel",
    response_model=DocumentResponse,
    dependencies=[Depends(require_permission("inventory.documents.cancel"))],
)
async def cancel_document(
    document_id: UUID,
    payload: CancelDocumentPayload,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> DocumentResponse:
    return DocumentResponse.model_validate(
        await DocumentService(unit_of_work).cancel(document_id, payload.reason, actor_id=user_id)
    )
