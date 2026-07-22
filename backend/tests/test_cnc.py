from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import ConflictError
from app.modules.cnc.application.services import (
    CncMachineService,
    CncPartService,
    CncProgramService,
    CncSheetPlanService,
    CncWorkOrderService,
)
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection
from tests.test_inventory import create_inventory_fixture


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
        yield unit_of_work  # type: ignore[misc]
    except Exception:
        await unit_of_work.rollback()
        raise


async def create_cnc_fixture(db_session: AsyncSession):
    data = await create_inventory_fixture(db_session)
    async with service_context(db_session) as unit_of_work:
        machine = await CncMachineService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "site_id": data["site"].id,
                "code": "CNC-01",
                "name": "Верстат ЧПК 01",
                "machine_type": "router",
            },
            actor_id=data["admin"].id,
            user=data["admin"],
        )
        program = await CncProgramService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "code": "BOX-PART",
                "name": "Деталь ящика",
                "revision": "A",
                "file_type": "gcode",
                "source_file_name": "box-part.nc",
            },
            actor_id=data["admin"].id,
        )
        program = await CncProgramService(unit_of_work).approve(
            program.id, actor_id=data["admin"].id
        )
        part = await CncPartService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "inventory_item_id": data["item"].id,
                "code": "PART-001",
                "name": "Панель транспортного ящика",
                "material_item_id": data["item"].id,
            },
            actor_id=data["admin"].id,
        )
    return {**data, "machine": machine, "program": program, "part": part}


async def test_cnc_machine_unique_code_and_status_transition(db_session: AsyncSession) -> None:
    data = await create_cnc_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await CncMachineService(unit_of_work).create(
                {
                    "organization_id": data["organization"].id,
                    "site_id": data["site"].id,
                    "code": "CNC-01",
                    "name": "Duplicate",
                    "machine_type": "router",
                },
                actor_id=data["admin"].id,
                user=data["admin"],
            )
        machine = await CncMachineService(unit_of_work).set_status(
            data["machine"].id, "maintenance", actor_id=data["admin"].id, user=data["admin"]
        )

    assert machine.status == "maintenance"


async def test_cnc_program_approved_revision_is_immutable(db_session: AsyncSession) -> None:
    data = await create_cnc_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        with pytest.raises(ConflictError):
            await CncProgramService(unit_of_work).update(
                data["program"].id,
                {"revision": "B"},
                expected_version=data["program"].version,
                actor_id=data["admin"].id,
            )


async def test_cnc_sheet_plan_lines_and_approved_immutability(db_session: AsyncSession) -> None:
    data = await create_cnc_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        plan = await CncSheetPlanService(unit_of_work).create(
            {
                "organization_id": data["organization"].id,
                "plan_number": "NEST-001",
                "name": "Розкрій панелей",
                "material_item_id": data["item"].id,
                "sheet_length_mm": "2500",
                "sheet_width_mm": "1250",
                "thickness_mm": "12",
                "planned_sheet_quantity": "2",
                "estimated_utilization_percent": "82",
            },
            actor_id=data["admin"].id,
        )
        await CncSheetPlanService(unit_of_work).add_line(
            plan.id,
            {"cnc_part_id": data["part"].id, "quantity_per_sheet": "4"},
            actor_id=data["admin"].id,
        )
        plan = await CncSheetPlanService(unit_of_work).approve(plan.id, actor_id=data["admin"].id)
        with pytest.raises(ConflictError):
            await CncSheetPlanService(unit_of_work).update(
                plan.id,
                {"name": "Changed"},
                expected_version=plan.version,
                actor_id=data["admin"].id,
            )


async def test_cnc_work_order_queue_and_double_start_protection(db_session: AsyncSession) -> None:
    data = await create_cnc_fixture(db_session)

    async with service_context(db_session) as unit_of_work:
        service = CncWorkOrderService(unit_of_work)
        first = await service.create(
            _work_order_payload(data, "CNC-WO-001"),
            actor_id=data["admin"].id,
            user=data["admin"],
        )
        first = await service.transition(
            first.id, "planned", actor_id=data["admin"].id, user=data["admin"]
        )
        first = await service.transition(
            first.id, "queued", actor_id=data["admin"].id, user=data["admin"]
        )
        first = await service.transition(
            first.id, "setup", actor_id=data["admin"].id, user=data["admin"]
        )
        second = await service.create(
            _work_order_payload(data, "CNC-WO-002"),
            actor_id=data["admin"].id,
            user=data["admin"],
        )
        second = await service.transition(
            second.id, "planned", actor_id=data["admin"].id, user=data["admin"]
        )
        second = await service.transition(
            second.id, "queued", actor_id=data["admin"].id, user=data["admin"]
        )
        with pytest.raises(ConflictError):
            await service.transition(
                second.id, "setup", actor_id=data["admin"].id, user=data["admin"]
            )
        orders, total = await service.list_orders(
            filters={"organization_id": data["organization"].id},
            page=PageRequest(page=1, page_size=10),
            sort_by="work_order_number",
            sort_direction=SortDirection.ASC,
            user=data["admin"],
        )

    assert total == 2
    assert [order.work_order_number for order in orders] == ["CNC-WO-001", "CNC-WO-002"]


def _work_order_payload(data: dict[str, object], number: str) -> dict[str, object]:
    return {
        "organization_id": data["organization"].id,
        "work_order_number": number,
        "name": number,
        "cnc_part_id": data["part"].id,
        "program_id": data["program"].id,
        "machine_id": data["machine"].id,
        "site_id": data["site"].id,
        "source_warehouse_id": data["warehouse"].id,
        "output_warehouse_id": data["warehouse"].id,
        "planned_quantity": "5",
        "unit_of_measure_id": data["unit"].id,
    }
