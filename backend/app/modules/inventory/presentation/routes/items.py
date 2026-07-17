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
    "/units",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.units.manage"))],
)
async def create_unit(
    payload: UnitCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> UnitResponse:
    return UnitResponse.model_validate(
        await CatalogService(unit_of_work).create_unit(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/units",
    response_model=PaginatedResponse[UnitResponse],
    dependencies=[Depends(require_permission("inventory.units.read"))],
)
async def list_units(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[UnitResponse]:
    items, total = await CatalogService(unit_of_work).list_units(
        filters={
            "organization_id": organization_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, UnitResponse)


@router.get(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("inventory.units.read"))],
)
async def get_unit(unit_id: UUID, unit_of_work: UnitOfWorkDependency) -> UnitResponse:
    return UnitResponse.model_validate(await CatalogService(unit_of_work).get_unit(unit_id))


@router.patch(
    "/units/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("inventory.units.manage"))],
)
async def update_unit(
    unit_id: UUID,
    payload: UnitUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> UnitResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return UnitResponse.model_validate(
        await CatalogService(unit_of_work).update_unit(
            unit_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.units.manage"))],
)
async def delete_unit(
    unit_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await CatalogService(unit_of_work).update_unit(
        unit_id, {"is_active": False}, expected_version=None, actor_id=user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.categories.manage"))],
)
async def create_category(
    payload: CategoryCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> CategoryResponse:
    return CategoryResponse.model_validate(
        await CatalogService(unit_of_work).create_category(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/categories",
    response_model=PaginatedResponse[CategoryResponse],
    dependencies=[Depends(require_permission("inventory.categories.read"))],
)
async def list_categories(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    parent_id: UUID | None = None,
    name: str | None = None,
    code: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[CategoryResponse]:
    items, total = await CatalogService(unit_of_work).list_categories(
        filters={
            "organization_id": organization_id,
            "parent_id": parent_id,
            "name": name,
            "code": code,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, CategoryResponse)


@router.get(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_permission("inventory.categories.read"))],
)
async def get_category(category_id: UUID, unit_of_work: UnitOfWorkDependency) -> CategoryResponse:
    return CategoryResponse.model_validate(
        await CatalogService(unit_of_work).get_category(category_id)
    )


@router.patch(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_permission("inventory.categories.manage"))],
)
async def update_category(
    category_id: UUID,
    payload: CategoryUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> CategoryResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return CategoryResponse.model_validate(
        await CatalogService(unit_of_work).update_category(
            category_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.categories.manage"))],
)
async def delete_category(
    category_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await CatalogService(unit_of_work).update_category(
        category_id, {"is_active": False}, expected_version=None, actor_id=user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.items.manage"))],
)
async def create_item(
    payload: ItemCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> ItemResponse:
    return ItemResponse.model_validate(
        await CatalogService(unit_of_work).create_item(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/items",
    response_model=PaginatedResponse[ItemResponse],
    dependencies=[Depends(require_permission("inventory.items.read"))],
)
async def list_items(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    category_id: UUID | None = None,
    item_type: ItemType | None = None,
    search: str | None = None,
    barcode: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[ItemResponse]:
    items, total = await CatalogService(unit_of_work).list_items(
        filters={
            "organization_id": organization_id,
            "category_id": category_id,
            "item_type": item_type,
            "search": search,
            "barcode": barcode,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, ItemResponse)


@router.get(
    "/items/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(require_permission("inventory.items.read"))],
)
async def get_item(item_id: UUID, unit_of_work: UnitOfWorkDependency) -> ItemResponse:
    return ItemResponse.model_validate(await CatalogService(unit_of_work).get_item(item_id))


@router.patch(
    "/items/{item_id}",
    response_model=ItemResponse,
    dependencies=[Depends(require_permission("inventory.items.manage"))],
)
async def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> ItemResponse:
    data = payload.model_dump(exclude_unset=True)
    version = data.pop("version")
    return ItemResponse.model_validate(
        await CatalogService(unit_of_work).update_item(
            item_id, data, expected_version=version, actor_id=user_id
        )
    )


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("inventory.items.manage"))],
)
async def delete_item(
    item_id: UUID, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> Response:
    await CatalogService(unit_of_work).deactivate_item(item_id, actor_id=user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/lots",
    response_model=LotResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.tracking.manage"))],
)
async def create_lot(
    payload: LotCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> LotResponse:
    return LotResponse.model_validate(
        await TrackingService(unit_of_work).create_lot(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/lots",
    response_model=PaginatedResponse[LotResponse],
    dependencies=[Depends(require_permission("inventory.tracking.read"))],
)
async def list_lots(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    item_id: UUID | None = None,
    lot_number: str | None = None,
    is_active: bool | None = None,
) -> PaginatedResponse[LotResponse]:
    items, total = await TrackingService(unit_of_work).list_lots(
        filters={
            "organization_id": organization_id,
            "item_id": item_id,
            "lot_number": lot_number,
            "is_active": is_active,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, LotResponse)


@router.get(
    "/lots/{lot_id}",
    response_model=LotResponse,
    dependencies=[Depends(require_permission("inventory.tracking.read"))],
)
async def get_lot(lot_id: UUID, unit_of_work: UnitOfWorkDependency) -> LotResponse:
    return LotResponse.model_validate(await TrackingService(unit_of_work).get_lot(lot_id))


@router.post(
    "/serials",
    response_model=SerialResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("inventory.tracking.manage"))],
)
async def create_serial(
    payload: SerialCreate, unit_of_work: UnitOfWorkDependency, user_id: CurrentUserIdDependency
) -> SerialResponse:
    return SerialResponse.model_validate(
        await TrackingService(unit_of_work).create_serial(payload.model_dump(), actor_id=user_id)
    )


@router.get(
    "/serials",
    response_model=PaginatedResponse[SerialResponse],
    dependencies=[Depends(require_permission("inventory.tracking.read"))],
)
async def list_serials(
    unit_of_work: UnitOfWorkDependency,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    sort_by: str = "created_at",
    sort_direction: SortDirectionQuery = SortDirection.DESC,
    organization_id: UUID | None = None,
    item_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    serial_number: str | None = None,
    status_filter: SerialStatusQuery = None,
) -> PaginatedResponse[SerialResponse]:
    items, total = await TrackingService(unit_of_work).list_serials(
        filters={
            "organization_id": organization_id,
            "item_id": item_id,
            "warehouse_id": warehouse_id,
            "serial_number": serial_number,
            "status": status_filter,
        },
        page=PageRequest(page=page, page_size=page_size),
        sort_by=sort_by,
        sort_direction=sort_direction,
    )
    return _page(items, total, page, page_size, SerialResponse)


@router.get(
    "/serials/{serial_id}",
    response_model=SerialResponse,
    dependencies=[Depends(require_permission("inventory.tracking.read"))],
)
async def get_serial(serial_id: UUID, unit_of_work: UnitOfWorkDependency) -> SerialResponse:
    return SerialResponse.model_validate(await TrackingService(unit_of_work).get_serial(serial_id))


@router.patch(
    "/serials/{serial_id}/status",
    response_model=SerialResponse,
    dependencies=[Depends(require_permission("inventory.tracking.manage"))],
)
async def update_serial_status(
    serial_id: UUID,
    payload: SerialStatusUpdate,
    unit_of_work: UnitOfWorkDependency,
    user_id: CurrentUserIdDependency,
) -> SerialResponse:
    return SerialResponse.model_validate(
        await TrackingService(unit_of_work).update_serial_status(
            serial_id, payload.status, actor_id=user_id
        )
    )
