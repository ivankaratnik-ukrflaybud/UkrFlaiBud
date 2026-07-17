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
    "/warehouses",
    response_model=WarehouseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.warehouses.manage"))],
)
async def create_warehouse(
    payload: WarehouseCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> WarehouseResponse:
    return WarehouseResponse.model_validate(
        await WarehouseService(unit_of_work).create(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/warehouses",
    response_model=PaginatedResponse[WarehouseResponse],
    dependencies=[Depends(require_permission("inventory.warehouses.read"))],
)
async def list_warehouses(
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    site_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[WarehouseResponse]:
    items, total = await WarehouseService(unit_of_work).list(
        filters={
            "organization_id": organization_id,
            "site_id": site_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, WarehouseResponse)


@router.get(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(require_permission("inventory.warehouses.read"))],
)
async def get_warehouse(
    warehouse_id: UUID, unit_of_work: UnitOfWorkDependency, user: CurrentUserDependency
) -> WarehouseResponse:
    await InventoryScopeService(unit_of_work).ensure_warehouse_access(user, warehouse_id)
    return WarehouseResponse.model_validate(await WarehouseService(unit_of_work).get(warehouse_id))


@router.patch(
    "/warehouses/{warehouse_id}",
    response_model=WarehouseResponse,
    dependencies=[Depends(require_permission("inventory.warehouses.manage"))],
)
async def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> WarehouseResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return WarehouseResponse.model_validate(
        await WarehouseService(unit_of_work).update(
            warehouse_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/warehouses/{warehouse_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.warehouses.manage"))],
)
async def delete_warehouse(
    warehouse_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await WarehouseService(unit_of_work).deactivate(warehouse_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
