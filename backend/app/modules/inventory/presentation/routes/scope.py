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


@identity_scope_router.get(
    "/users/{user_id}/inventory-scope",
    response_model=UserInventoryScopeResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def get_user_inventory_scope(
    user_id: UUID, unit_of_work: UnitOfWorkDependency
) -> UserInventoryScopeResponse:
    return UserInventoryScopeResponse.model_validate(
        await InventoryScopeService(unit_of_work).get_user_scope(user_id)
    )


@identity_scope_router.put(
    "/users/{user_id}/inventory-scope",
    response_model=UserInventoryScopeResponse,
    dependencies=[Depends(require_permission("users.manage"))],
)
async def set_user_inventory_scope(
    user_id: UUID,
    payload: UserInventoryScopeUpdate,
    unit_of_work: UnitOfWorkDependency,
    actor_id: CurrentUserIdDependency,
) -> UserInventoryScopeResponse:
    return UserInventoryScopeResponse.model_validate(
        await InventoryScopeService(unit_of_work).set_user_scope(
            user_id, payload.site_ids, payload.warehouse_ids, actor_id=actor_id
        )
    )
