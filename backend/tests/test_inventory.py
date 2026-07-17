from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ConflictError, PermissionDeniedError, ValidationError
from app.modules.identity.infrastructure.models import UserModel
from app.modules.inventory.application.services import (
    CatalogService,
    DocumentService,
    InventoryScopeService,
    LocationService,
    SiteService,
    StockService,
    WarehouseService,
)
from app.modules.inventory.infrastructure.models import InventoryMovementModel
from app.modules.organizations.application.services import OrganizationService
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection


class UnitOfWorkStub:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self._session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    async def flush(self) -> None:
        await self.session.flush()

    async def refresh(self, entity: object, attribute_names: list[str] | None = None) -> None:
        await self.session.refresh(entity, attribute_names=attribute_names)


@asynccontextmanager
async def service_context(db_session: AsyncSession) -> AsyncGenerator[SQLAlchemyUnitOfWork]:
    unit_of_work = UnitOfWorkStub(db_session)
    try:
        yield unit_of_work
    except Exception:
        await unit_of_work.rollback()
        raise


async def create_inventory_fixture(db_session: AsyncSession):
    async with service_context(db_session) as unit_of_work:
        organization = await OrganizationService(unit_of_work).create(
            {
                "name": "UkrFlyBud",
                "short_name": "UFB",
                "legal_name": "UkrFlyBud LLC",
                "edrpou": "12345678",
                "is_active": True,
            }
        )
        admin = UserModel(
            email="admin@example.com",
            normalized_email="admin@example.com",
            password_hash="hash",
            display_name="Admin",
            is_active=True,
            is_superuser=True,
        )
        restricted = UserModel(
            email="warehouse@example.com",
            normalized_email="warehouse@example.com",
            password_hash="hash",
            display_name="Warehouse",
            is_active=True,
            is_superuser=False,
        )
        db_session.add_all([admin, restricted])
        await db_session.flush()
        site = await SiteService(unit_of_work).create(
            {"organization_id": organization.id, "code": "KYIV", "name": "Київ"},
            actor_id=admin.id,
        )
        other_site = await SiteService(unit_of_work).create(
            {"organization_id": organization.id, "code": "TALNE", "name": "Тальне"},
            actor_id=admin.id,
        )
        warehouse = await WarehouseService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "site_id": site.id,
                "code": "KYIV-MAIN",
                "name": "Склад Київ",
                "warehouse_type": "main",
            },
            actor_id=admin.id,
        )
        other_warehouse = await WarehouseService(unit_of_work).create(
            {
                "organization_id": organization.id,
                "site_id": other_site.id,
                "code": "TALNE-MAIN",
                "name": "Склад Тальне",
                "warehouse_type": "main",
            },
            actor_id=admin.id,
        )
        unit = await CatalogService(unit_of_work).create_unit(
            {
                "organization_id": organization.id,
                "code": "PCS",
                "name": "штука",
                "symbol": "шт",
                "precision": 0,
            },
            actor_id=admin.id,
        )
        category = await CatalogService(unit_of_work).create_category(
            {
                "organization_id": organization.id,
                "code": "ELEC",
                "name": "Електроніка",
            },
            actor_id=admin.id,
        )
        item = await CatalogService(unit_of_work).create_item(
            {
                "organization_id": organization.id,
                "sku": "MOTOR-001",
                "name": "Двигун",
                "category_id": category.id,
                "unit_of_measure_id": unit.id,
                "item_type": "component",
                "minimum_stock": 2,
            },
            actor_id=admin.id,
        )
    return {
        "organization": organization,
        "admin": admin,
        "restricted": restricted,
        "site": site,
        "other_site": other_site,
        "warehouse": warehouse,
        "other_warehouse": other_warehouse,
        "unit": unit,
        "category": category,
        "item": item,
    }


async def test_sites_warehouses_and_scope_filtering(db_session: AsyncSession) -> None:
    data = await create_inventory_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await SiteService(unit_of_work).create(
                {
                    "organization_id": data["organization"].id,
                    "code": "KYIV",
                    "name": "Duplicate",
                },
                actor_id=data["admin"].id,
            )
        await InventoryScopeService(unit_of_work).set_user_scope(
            data["restricted"].id,
            [],
            [data["warehouse"].id],
            actor_id=data["admin"].id,
        )
        warehouses, total = await WarehouseService(unit_of_work).list(
            filters={"organization_id": data["organization"].id},
            page=PageRequest(page=1, page_size=50),
            sort_by="name",
            sort_direction=SortDirection.ASC,
            user=data["restricted"],
        )
        with pytest.raises(PermissionDeniedError):
            await InventoryScopeService(unit_of_work).ensure_warehouse_access(
                data["restricted"], data["other_warehouse"].id
            )

    assert total == 1
    assert [warehouse.id for warehouse in warehouses] == [data["warehouse"].id]


async def test_location_hierarchy_cycle_and_cross_warehouse_parent(
    db_session: AsyncSession,
) -> None:
    data = await create_inventory_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        parent = await LocationService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "warehouse_id": data["warehouse"].id,
                "code": "A",
                "name": "Зона A",
                "location_type": "zone",
            },
            actor_id=data["admin"].id,
        )
        child = await LocationService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "warehouse_id": data["warehouse"].id,
                "parent_id": parent.id,
                "code": "A-1",
                "name": "Полиця A-1",
                "location_type": "shelf",
            },
            actor_id=data["admin"].id,
        )
        other_parent = await LocationService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "warehouse_id": data["other_warehouse"].id,
                "code": "B",
                "name": "Зона B",
                "location_type": "zone",
            },
            actor_id=data["admin"].id,
        )

        with pytest.raises(ValidationError):
            await LocationService(unit_of_work).update(
                parent.id,
                {"parent_id": child.id},
                expected_version=parent.version,
                actor_id=data["admin"].id,
            )
        with pytest.raises(ValidationError):
            await LocationService(unit_of_work).update(
                child.id,
                {"parent_id": other_parent.id},
                expected_version=child.version,
                actor_id=data["admin"].id,
            )


async def test_catalog_duplicates_min_max_and_deactivation(db_session: AsyncSession) -> None:
    data = await create_inventory_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await CatalogService(unit_of_work).create_unit(
                {
                    "organization_id": data["organization"].id,
                    "code": "PCS",
                    "name": "duplicate",
                    "symbol": "dup",
                    "precision": 0,
                },
                actor_id=data["admin"].id,
            )
        with pytest.raises(ConflictError):
            await CatalogService(unit_of_work).create_item(
                {
                    "organization_id": data["organization"].id,
                    "sku": "MOTOR-001",
                    "name": "Duplicate",
                    "category_id": data["category"].id,
                    "unit_of_measure_id": data["unit"].id,
                    "item_type": "component",
                },
                actor_id=data["admin"].id,
            )
        with pytest.raises(ValidationError):
            await CatalogService(unit_of_work).create_item(
                {
                    "organization_id": data["organization"].id,
                    "sku": "BAD-STOCK",
                    "name": "Bad",
                    "category_id": data["category"].id,
                    "unit_of_measure_id": data["unit"].id,
                    "item_type": "component",
                    "minimum_stock": 10,
                    "maximum_stock": 1,
                },
                actor_id=data["admin"].id,
            )
        deactivated = await CatalogService(unit_of_work).deactivate_item(
            data["item"].id, actor_id=data["admin"].id
        )

    assert deactivated.is_active is False


async def test_post_receipt_issue_transfer_and_cancel_reversal(db_session: AsyncSession) -> None:
    data = await create_inventory_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        receipt = await DocumentService(unit_of_work).create_draft(
            {
                "organization_id": data["organization"].id,
                "document_type": "receipt",
                "destination_warehouse_id": data["warehouse"].id,
            },
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).add_line(
            receipt.id,
            {"item_id": data["item"].id, "quantity": 10},
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).post(
            receipt.id, actor_id=data["admin"].id, user=data["admin"]
        )

        issue = await DocumentService(unit_of_work).create_draft(
            {
                "organization_id": data["organization"].id,
                "document_type": "issue",
                "source_warehouse_id": data["warehouse"].id,
            },
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).add_line(
            issue.id,
            {"item_id": data["item"].id, "quantity": 3},
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).post(
            issue.id, actor_id=data["admin"].id, user=data["admin"]
        )

        transfer = await DocumentService(unit_of_work).create_draft(
            {
                "organization_id": data["organization"].id,
                "document_type": "transfer",
                "source_warehouse_id": data["warehouse"].id,
                "destination_warehouse_id": data["other_warehouse"].id,
            },
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).add_line(
            transfer.id,
            {"item_id": data["item"].id, "quantity": 2},
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).post(
            transfer.id, actor_id=data["admin"].id, user=data["admin"]
        )

        source_balances, _ = await StockService(unit_of_work).list_balances(
            filters={"warehouse_id": data["warehouse"].id},
            page=PageRequest(page=1, page_size=50),
            sort_by="updated_at",
            sort_direction=SortDirection.DESC,
            user=data["admin"],
        )
        destination_balances, _ = await StockService(unit_of_work).list_balances(
            filters={"warehouse_id": data["other_warehouse"].id},
            page=PageRequest(page=1, page_size=50),
            sort_by="updated_at",
            sort_direction=SortDirection.DESC,
            user=data["admin"],
        )
        source_quantity_before_cancel = sum(balance.quantity for balance in source_balances)
        destination_quantity_before_cancel = sum(
            balance.quantity for balance in destination_balances
        )
        await DocumentService(unit_of_work).cancel(
            transfer.id, "Помилкове переміщення", actor_id=data["admin"].id
        )

    assert source_quantity_before_cancel == 5
    assert destination_quantity_before_cancel == 2

    movements = (
        await db_session.scalars(
            select(InventoryMovementModel).where(InventoryMovementModel.document_id == transfer.id)
        )
    ).all()
    assert any(movement.movement_kind == "reversal" for movement in movements)


async def test_insufficient_stock_rolls_back_without_partial_movement(
    db_session: AsyncSession,
) -> None:
    data = await create_inventory_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        document = await DocumentService(unit_of_work).create_draft(
            {
                "organization_id": data["organization"].id,
                "document_type": "issue",
                "source_warehouse_id": data["warehouse"].id,
            },
            actor_id=data["admin"].id,
        )
        await DocumentService(unit_of_work).add_line(
            document.id,
            {"item_id": data["item"].id, "quantity": 1},
            actor_id=data["admin"].id,
        )
        document_id = document.id
        with pytest.raises(ConflictError):
            await DocumentService(unit_of_work).post(
                document.id, actor_id=data["admin"].id, user=data["admin"]
            )

    movements = (
        await db_session.scalars(
            select(InventoryMovementModel).where(InventoryMovementModel.document_id == document_id)
        )
    ).all()
    assert movements == []
