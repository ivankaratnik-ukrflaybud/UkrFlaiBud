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
    "/sites",
    response_model=SiteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.sites.manage"))],
)
async def create_site(
    payload: SiteCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> SiteResponse:
    site = await SiteService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    return SiteResponse.model_validate(site)


@router.get(
    "/sites",
    response_model=PaginatedResponse[SiteResponse],
    dependencies=[Depends(require_permission("inventory.sites.read"))],
)
async def list_sites(
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[SiteResponse]:
    items, total = await SiteService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, SiteResponse)


@router.get(
    "/sites/{site_id}",
    response_model=SiteResponse,
    dependencies=[Depends(require_permission("inventory.sites.read"))],
)
async def get_site(site_id: UUID, unit_of_work: UnitOfWorkDependency) -> SiteResponse:
    return SiteResponse.model_validate(await SiteService(unit_of_work).get(site_id))


@router.patch(
    "/sites/{site_id}",
    response_model=SiteResponse,
    dependencies=[Depends(require_permission("inventory.sites.manage"))],
)
async def update_site(
    site_id: UUID,
    payload: SiteUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> SiteResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return SiteResponse.model_validate(
        await SiteService(unit_of_work).update(
            site_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/sites/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.sites.manage"))],
)
async def delete_site(
    site_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await SiteService(unit_of_work).deactivate(site_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
