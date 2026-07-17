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


@router.get(
    "/stock",
    response_model=PaginatedResponse[StockBalanceResponse],
    dependencies=[Depends(require_permission("inventory.stock.read"))],
)
async def list_stock(
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "updated_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    item_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    location_id: UUID | None = None,
    lot_id: UUID | None = None,
) -> PaginatedResponse[StockBalanceResponse]:
    items, total = await StockService(unit_of_work).list_balances(
        filters={
            "organization_id": organization_id,
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "location_id": location_id,
            "lot_id": lot_id,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, StockBalanceResponse)


@router.get(
    "/stock/items/{item_id}",
    response_model=PaginatedResponse[StockBalanceResponse],
    dependencies=[Depends(require_permission("inventory.stock.read"))],
)
async def get_item_stock(
    item_id: UUID,
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> PaginatedResponse[StockBalanceResponse]:
    items, total = await StockService(unit_of_work).list_balances(
        filters={"item_id": item_id},
        page=PageRequest(page=page, page_size=page_size),
        sort_by="updated_at",
        sort_direction=SortDirection.DESC,
        user=user,
    )
    return _page(items, total, page, page_size, StockBalanceResponse)


@router.get(
    "/movements",
    response_model=PaginatedResponse[MovementResponse],
    dependencies=[Depends(require_permission("inventory.stock.read"))],
)
async def list_movements(
    unit_of_work: UnitOfWorkDependency,
    user: CurrentUserDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "occurred_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    item_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    document_id: UUID | None = None,
) -> PaginatedResponse[MovementResponse]:
    items, total = await StockService(unit_of_work).list_movements(
        filters={
            "organization_id": organization_id,
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "document_id": document_id,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
        user=user,
    )
    return _page(items, total, page, page_size, MovementResponse)


@router.get("/low-stock", dependencies=[Depends(require_permission("inventory.stock.read"))])
async def low_stock(
    organization_id: UUID, unit_of_work: UnitOfWorkDependency, user: CurrentUserDependency
) -> list[dict[str, object]]:
    return await StockService(unit_of_work).low_stock(organization_id, user=user)
