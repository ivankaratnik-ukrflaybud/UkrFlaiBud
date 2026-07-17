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
    "/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.locations.manage"))],
)
async def create_location(
    payload: LocationCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> LocationResponse:
    return LocationResponse.model_validate(
        await LocationService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/locations",
    response_model=PaginatedResponse[LocationResponse],
    dependencies=[Depends(require_permission("inventory.locations.read"))],
)
async def list_locations(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[LocationResponse]:
    items, total = await LocationService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "warehouse_id": warehouse_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, LocationResponse)


@router.get(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("inventory.locations.read"))],
)
async def get_location(location_id: UUID, unit_of_work: UnitOfWorkDependency) -> LocationResponse:
    return LocationResponse.model_validate(await LocationService(unit_of_work).get(location_id))


@router.patch(
    "/locations/{location_id}",
    response_model=LocationResponse,
    dependencies=[Depends(require_permission("inventory.locations.manage"))],
)
async def update_location(
    location_id: UUID,
    payload: LocationUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> LocationResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return LocationResponse.model_validate(
        await LocationService(unit_of_work).update(
            location_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/locations/{location_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.locations.manage"))],
)
async def delete_location(
    location_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await LocationService(unit_of_work).deactivate(location_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
