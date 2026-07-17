# ruff: noqa: F401,I001
from .common import (
    Any,
    UTC,
    datetime,
    Decimal,
    UUID,
    delete,
    func,
    or_,
    select,
    AsyncSession,
    AuditAction,
    AuditLog,
    OutboxEvent,
    ConflictError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
    UserService,
    UserModel,
    InventoryDocumentStatus,
    InventoryDocumentType,
    InventoryMovementKind,
    ItemType,
    SerialStatus,
    InventoryDocumentLineModel,
    InventoryDocumentLineSerialModel,
    InventoryDocumentModel,
    InventoryLotModel,
    InventoryMovementModel,
    InventorySerialModel,
    ItemCategoryModel,
    ItemModel,
    SiteModel,
    StockBalanceModel,
    StorageLocationModel,
    UnitOfMeasureModel,
    WarehouseModel,
    CategoryRepository,
    DocumentLineRepository,
    DocumentRepository,
    InventoryScopeRepository,
    ItemRepository,
    LotRepository,
    MovementRepository,
    SerialRepository,
    SiteRepository,
    StockBalanceRepository,
    StorageLocationRepository,
    UnitRepository,
    WarehouseRepository,
    EmployeeModel,
    OrganizationModel,
    SQLAlchemyAuditLogRepository,
    SQLAlchemyOutboxRepository,
    SQLAlchemyUnitOfWork,
    PageRequest,
    SortDirection,
    STOCK_IN_TYPES,
    STOCK_OUT_TYPES,
    InventoryService,
    _apply_updates,
)
from .catalog import CatalogService
from .locations import LocationService
from .scope import InventoryScopeService
from .tracking import TrackingService
from .warehouses import WarehouseService


class DocumentService(InventoryService):
    async def create_draft(self, data: dict[str, Any], *, actor_id: UUID) -> InventoryDocumentModel:
        await self._validate_document_header(data)
        if not data.get("document_number"):
            data["document_number"] = await self._next_document_number(data["organization_id"])
        repository = DocumentRepository(self.session)
        if await repository.exists_by_number(data["organization_id"], data["document_number"]):
            raise ConflictError("Document number must be unique.", {"field": "document_number"})
        document = await repository.create(
            InventoryDocumentModel(
                **data, status=InventoryDocumentStatus.DRAFT.value, created_by_user_id=actor_id
            )
        )
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="inventory_document",
            entity_id=document.id,
            actor_id=actor_id,
            after={"number": document.document_number},
        )
        await self._commit()
        return document

    async def get(self, document_id: UUID) -> InventoryDocumentModel:
        document = await DocumentRepository(self.session).get(document_id)
        if document is None:
            raise EntityNotFoundError("Document not found.", {"id": str(document_id)})
        return document

    async def list_documents(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
        user: UserModel | None = None,
    ) -> tuple[list[InventoryDocumentModel], int]:
        if user and not user.is_superuser:
            allowed = await InventoryScopeService(self.unit_of_work).accessible_warehouse_ids(user)
            if not allowed:
                return [], 0
            filters = {**filters, "warehouse_ids": allowed}
        return await DocumentRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def update_header(
        self,
        document_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> InventoryDocumentModel:
        document = await self.get(document_id)
        self._ensure_draft(document)
        self._ensure_version(document, expected_version)
        merged = {
            "organization_id": data.get("organization_id", document.organization_id),
            "document_type": data.get("document_type", document.document_type),
            "source_warehouse_id": data.get("source_warehouse_id", document.source_warehouse_id),
            "destination_warehouse_id": data.get(
                "destination_warehouse_id", document.destination_warehouse_id
            ),
            "responsible_employee_id": data.get(
                "responsible_employee_id", document.responsible_employee_id
            ),
        }
        await self._validate_document_header(merged)
        _apply_updates(document, data)
        await DocumentRepository(self.session).update(document)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_document",
            entity_id=document.id,
            actor_id=actor_id,
        )
        await self._commit()
        return document

    async def add_line(
        self, document_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> InventoryDocumentLineModel:
        document = await self.get(document_id)
        self._ensure_draft(document)
        await self._validate_line(document, data)
        repository = DocumentLineRepository(self.session)
        line_number = data.get("line_number") or await repository.next_line_number(document.id)
        line = await repository.create(
            InventoryDocumentLineModel(**data, document_id=document.id, line_number=line_number)
        )
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_document",
            entity_id=document.id,
            actor_id=actor_id,
            after={"line_added": str(line.id)},
        )
        await self._commit()
        return line

    async def update_line(
        self,
        document_id: UUID,
        line_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> InventoryDocumentLineModel:
        document = await self.get(document_id)
        self._ensure_draft(document)
        line = await DocumentLineRepository(self.session).get(line_id)
        if line is None or line.document_id != document_id:
            raise EntityNotFoundError("Document line not found.", {"id": str(line_id)})
        self._ensure_version(line, expected_version)
        merged = {
            "item_id": data.get("item_id", line.item_id),
            "quantity": data.get("quantity", line.quantity),
            "source_location_id": data.get("source_location_id", line.source_location_id),
            "destination_location_id": data.get(
                "destination_location_id", line.destination_location_id
            ),
            "lot_id": data.get("lot_id", line.lot_id),
        }
        await self._validate_line(document, merged)
        _apply_updates(line, data)
        await DocumentLineRepository(self.session).update(line)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_document",
            entity_id=document.id,
            actor_id=actor_id,
            after={"line_updated": str(line.id)},
        )
        await self._commit()
        return line

    async def delete_line(self, document_id: UUID, line_id: UUID, *, actor_id: UUID) -> None:
        document = await self.get(document_id)
        self._ensure_draft(document)
        line = await DocumentLineRepository(self.session).get(line_id)
        if line is None or line.document_id != document_id:
            raise EntityNotFoundError("Document line not found.", {"id": str(line_id)})
        await self.session.delete(line)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="inventory_document",
            entity_id=document.id,
            actor_id=actor_id,
            after={"line_deleted": str(line.id)},
        )
        await self._commit()

    async def attach_serials(
        self, document_id: UUID, line_id: UUID, serial_ids: list[UUID]
    ) -> None:
        document = await self.get(document_id)
        self._ensure_draft(document)
        line = await DocumentLineRepository(self.session).get(line_id)
        if line is None or line.document_id != document_id:
            raise EntityNotFoundError("Document line not found.", {"id": str(line_id)})
        item = await CatalogService(self.unit_of_work).get_item(line.item_id)
        if not item.track_serial_numbers:
            raise ValidationError("Serials can only be attached to serial-tracked items.")
        if Decimal(len(serial_ids)) != Decimal(line.quantity):
            raise ValidationError("Serial quantity must match line quantity.")
        await self.session.execute(
            delete(InventoryDocumentLineSerialModel).where(
                InventoryDocumentLineSerialModel.line_id == line_id
            )
        )
        for serial_id in serial_ids:
            serial = await TrackingService(self.unit_of_work).get_serial(serial_id)
            if serial.item_id != item.id:
                raise ValidationError("Serial item must match document line item.")
            self.session.add(InventoryDocumentLineSerialModel(line_id=line_id, serial_id=serial_id))
        await self._commit()

    async def lines(self, document_id: UUID) -> list[InventoryDocumentLineModel]:
        await self.get(document_id)
        return await DocumentLineRepository(self.session).list_for_document(document_id)

    async def post(
        self, document_id: UUID, *, actor_id: UUID, user: UserModel | None = None
    ) -> InventoryDocumentModel:
        try:
            document = await self.get(document_id)
            self._ensure_draft(document)
            if user:
                await InventoryScopeService(self.unit_of_work).ensure_warehouse_access(
                    user, document.source_warehouse_id
                )
                await InventoryScopeService(self.unit_of_work).ensure_warehouse_access(
                    user, document.destination_warehouse_id
                )
            lines = await DocumentLineRepository(self.session).list_for_document(document.id)
            if not lines:
                raise ValidationError("Document must contain at least one line.")
            await self._validate_posting(document, lines)
            occurred_at = datetime.now(UTC)
            for line in lines:
                await self._post_line(document, line, occurred_at, actor_id)
            document.status = InventoryDocumentStatus.POSTED.value
            document.posted_at = occurred_at
            document.posted_by_user_id = actor_id
            await DocumentRepository(self.session).update(document)
            await self._audit(
                action=AuditAction.UPDATE.value,
                entity_type="inventory_document",
                entity_id=document.id,
                actor_id=actor_id,
                after={"status": document.status},
            )
            await self._outbox(
                "inventory.document.posted",
                "inventory_document",
                document.id,
                {"document_number": document.document_number},
            )
            await self._commit()
            await self.unit_of_work.refresh(document)
            return document
        except Exception:
            await self.unit_of_work.rollback()
            raise

    async def cancel(
        self, document_id: UUID, reason: str | None, *, actor_id: UUID
    ) -> InventoryDocumentModel:
        try:
            document = await self.get(document_id)
            if document.status == InventoryDocumentStatus.CANCELLED.value:
                raise ConflictError("Cancelled documents cannot be reposted.")
            if document.status == InventoryDocumentStatus.DRAFT.value:
                document.status = InventoryDocumentStatus.CANCELLED.value
            else:
                if not reason:
                    raise ValidationError("Cancellation reason is required.", {"field": "reason"})
                movements = (
                    await MovementRepository(self.session).list(
                        filters={"document_id": document.id},
                        sort_by="occurred_at",
                        sort_direction=SortDirection.ASC,
                        limit=10_000,
                        offset=0,
                    )
                )[0]
                for movement in movements:
                    reversal = InventoryMovementModel(
                        organization_id=movement.organization_id,
                        document_id=movement.document_id,
                        document_line_id=movement.document_line_id,
                        item_id=movement.item_id,
                        warehouse_id=movement.warehouse_id,
                        location_id=movement.location_id,
                        lot_id=movement.lot_id,
                        serial_id=movement.serial_id,
                        quantity_delta=-movement.quantity_delta,
                        occurred_at=datetime.now(UTC),
                        movement_kind=InventoryMovementKind.REVERSAL.value,
                        reversal_of_movement_id=movement.id,
                        created_by_user_id=actor_id,
                    )
                    await MovementRepository(self.session).create(reversal)
                    await self._apply_balance_delta(
                        organization_id=movement.organization_id,
                        item_id=movement.item_id,
                        warehouse_id=movement.warehouse_id,
                        location_id=movement.location_id,
                        lot_id=movement.lot_id,
                        serial_id=movement.serial_id,
                        delta=-movement.quantity_delta,
                        allow_negative=True,
                    )
                document.status = InventoryDocumentStatus.CANCELLED.value
            document.cancelled_at = datetime.now(UTC)
            document.cancelled_by_user_id = actor_id
            document.cancellation_reason = reason
            await DocumentRepository(self.session).update(document)
            await self._audit(
                action=AuditAction.UPDATE.value,
                entity_type="inventory_document",
                entity_id=document.id,
                actor_id=actor_id,
                after={"status": document.status, "reason": reason},
            )
            await self._outbox(
                "inventory.document.cancelled",
                "inventory_document",
                document.id,
                {"document_number": document.document_number},
            )
            await self._commit()
            await self.unit_of_work.refresh(document)
            return document
        except Exception:
            await self.unit_of_work.rollback()
            raise

    async def _post_line(
        self,
        document: InventoryDocumentModel,
        line: InventoryDocumentLineModel,
        occurred_at: datetime,
        actor_id: UUID,
    ) -> None:
        document_type = InventoryDocumentType(document.document_type)
        if document_type == InventoryDocumentType.TRANSFER:
            await self._create_movement(
                document,
                line,
                document.source_warehouse_id,
                line.source_location_id,
                -line.quantity,
                InventoryMovementKind.TRANSFER_OUT,
                occurred_at,
                actor_id,
            )
            await self._create_movement(
                document,
                line,
                document.destination_warehouse_id,
                line.destination_location_id,
                line.quantity,
                InventoryMovementKind.TRANSFER_IN,
                occurred_at,
                actor_id,
            )
        elif document_type in STOCK_IN_TYPES:
            kind = InventoryMovementKind(document_type.value)
            await self._create_movement(
                document,
                line,
                document.destination_warehouse_id,
                line.destination_location_id,
                line.quantity,
                kind,
                occurred_at,
                actor_id,
            )
        else:
            kind = InventoryMovementKind(document_type.value)
            await self._create_movement(
                document,
                line,
                document.source_warehouse_id,
                line.source_location_id,
                -line.quantity,
                kind,
                occurred_at,
                actor_id,
            )

    async def _create_movement(
        self,
        document: InventoryDocumentModel,
        line: InventoryDocumentLineModel,
        warehouse_id: UUID | None,
        location_id: UUID | None,
        delta: Decimal,
        kind: InventoryMovementKind,
        occurred_at: datetime,
        actor_id: UUID,
    ) -> None:
        if warehouse_id is None:
            raise ValidationError("Warehouse is required for movement.")
        warehouse = await WarehouseService(self.unit_of_work).get(warehouse_id)
        movement = InventoryMovementModel(
            organization_id=document.organization_id,
            document_id=document.id,
            document_line_id=line.id,
            item_id=line.item_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            lot_id=line.lot_id,
            serial_id=None,
            quantity_delta=delta,
            occurred_at=occurred_at,
            movement_kind=kind.value,
            created_by_user_id=actor_id,
        )
        await MovementRepository(self.session).create(movement)
        await self._apply_balance_delta(
            organization_id=document.organization_id,
            item_id=line.item_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            lot_id=line.lot_id,
            serial_id=None,
            delta=delta,
            allow_negative=warehouse.allow_negative_stock,
        )

    async def _apply_balance_delta(
        self,
        *,
        organization_id: UUID,
        item_id: UUID,
        warehouse_id: UUID,
        location_id: UUID | None,
        lot_id: UUID | None,
        serial_id: UUID | None,
        delta: Decimal,
        allow_negative: bool,
    ) -> StockBalanceModel:
        repository = StockBalanceRepository(self.session)
        balance = await repository.get_dimension(
            organization_id=organization_id,
            item_id=item_id,
            warehouse_id=warehouse_id,
            location_id=location_id,
            lot_id=lot_id,
            serial_id=serial_id,
            for_update=True,
        )
        if balance is None:
            balance = await repository.create(
                StockBalanceModel(
                    organization_id=organization_id,
                    item_id=item_id,
                    warehouse_id=warehouse_id,
                    location_id=location_id,
                    lot_id=lot_id,
                    serial_id=serial_id,
                    quantity=Decimal("0"),
                )
            )
        next_quantity = Decimal(balance.quantity) + Decimal(delta)
        if next_quantity < 0 and not allow_negative:
            raise ConflictError("Insufficient stock.", {"field": "quantity"})
        balance.quantity = next_quantity
        await self.session.flush()
        return balance

    async def _validate_document_header(self, data: dict[str, Any]) -> None:
        document_type = InventoryDocumentType(data["document_type"])
        source_id = data.get("source_warehouse_id")
        destination_id = data.get("destination_warehouse_id")
        if document_type == InventoryDocumentType.TRANSFER:
            if not source_id or not destination_id:
                raise ValidationError("Transfer requires source and destination warehouses.")
            if source_id == destination_id:
                raise ValidationError("Source and destination warehouses must be different.")
        elif document_type in STOCK_IN_TYPES:
            if not destination_id:
                raise ValidationError("Destination warehouse is required.")
        elif not source_id:
            raise ValidationError("Source warehouse is required.")
        for warehouse_id in (source_id, destination_id):
            if warehouse_id is None:
                continue
            warehouse = await WarehouseService(self.unit_of_work).get(warehouse_id)
            if warehouse.organization_id != data["organization_id"]:
                raise ValidationError("Warehouse must belong to the same organization.")
            if not warehouse.is_active:
                raise ValidationError("Inactive warehouse cannot receive new documents.")
        await self._ensure_employee(data["organization_id"], data.get("responsible_employee_id"))

    async def _validate_line(self, document: InventoryDocumentModel, data: dict[str, Any]) -> None:
        item = await CatalogService(self.unit_of_work).get_item(data["item_id"])
        if item.organization_id != document.organization_id:
            raise ValidationError("Item must belong to the same organization.")
        if not item.is_active:
            raise ValidationError("Inactive item cannot be used in documents.")
        if item.item_type == ItemType.SERVICE.value:
            raise ValidationError("Service items cannot create physical stock movements.")
        if Decimal(str(data["quantity"])) <= 0:
            raise ValidationError("Quantity must be greater than zero.", {"field": "quantity"})
        if item.track_serial_numbers and Decimal(str(data["quantity"])) % 1 != 0:
            raise ValidationError("Serial-tracked quantities must be whole units.")
        if data.get("lot_id"):
            lot = await TrackingService(self.unit_of_work).get_lot(data["lot_id"])
            if lot.item_id != item.id:
                raise ValidationError("Lot item must match document line item.")
        await self._validate_line_location(
            document.source_warehouse_id, data.get("source_location_id")
        )
        await self._validate_line_location(
            document.destination_warehouse_id, data.get("destination_location_id")
        )

    async def _validate_line_location(
        self, warehouse_id: UUID | None, location_id: UUID | None
    ) -> None:
        if location_id is None:
            return
        if warehouse_id is None:
            raise ValidationError("Location requires warehouse.")
        location = await LocationService(self.unit_of_work).get(location_id)
        if location.warehouse_id != warehouse_id:
            raise ValidationError("Location must belong to the selected warehouse.")
        if not location.is_active:
            raise ValidationError("Inactive location cannot be used in documents.")

    async def _validate_posting(
        self, document: InventoryDocumentModel, lines: list[InventoryDocumentLineModel]
    ) -> None:
        for line in lines:
            await self._validate_line(
                document,
                {
                    "item_id": line.item_id,
                    "quantity": line.quantity,
                    "source_location_id": line.source_location_id,
                    "destination_location_id": line.destination_location_id,
                    "lot_id": line.lot_id,
                },
            )

    async def _next_document_number(self, organization_id: UUID) -> str:
        count = await self.session.scalar(
            select(func.count())
            .select_from(InventoryDocumentModel)
            .where(InventoryDocumentModel.organization_id == organization_id)
        )
        return f"INV-{datetime.now(UTC):%Y%m%d}-{(count or 0) + 1:05d}"

    def _ensure_draft(self, document: InventoryDocumentModel) -> None:
        if document.status != InventoryDocumentStatus.DRAFT.value:
            raise ValidationError("Posted document cannot be edited.")
