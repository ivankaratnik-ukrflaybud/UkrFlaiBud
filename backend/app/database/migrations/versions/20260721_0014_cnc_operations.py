"""Add CNC operations module.

Revision ID: 20260721_0014
Revises: 20260721_0013
Create Date: 2026-07-21 16:30:00.000000

"""

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

from app.modules.cnc.infrastructure.models import (
    CncExecutionLogModel,
    CncMachineModel,
    CncMaterialTransactionModel,
    CncOffcutModel,
    CncPartModel,
    CncProgramModel,
    CncSheetPlanLineModel,
    CncSheetPlanModel,
    CncToolModel,
    CncWorkOrderCommentModel,
    CncWorkOrderModel,
    CncWorkOrderOutputModel,
)

revision: str = "20260721_0014"
down_revision: str | None = "20260721_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CNC_TABLES: list[Any] = [
    CncMachineModel.__table__,
    CncToolModel.__table__,
    CncProgramModel.__table__,
    CncPartModel.__table__,
    CncSheetPlanModel.__table__,
    CncSheetPlanLineModel.__table__,
    CncWorkOrderModel.__table__,
    CncWorkOrderOutputModel.__table__,
    CncExecutionLogModel.__table__,
    CncMaterialTransactionModel.__table__,
    CncOffcutModel.__table__,
    CncWorkOrderCommentModel.__table__,
]

CNC_TABLE_NAMES_DOWNGRADE = [
    "cnc_work_order_comments",
    "cnc_offcuts",
    "cnc_material_transactions",
    "cnc_execution_logs",
    "cnc_work_order_outputs",
    "cnc_work_orders",
    "cnc_sheet_plan_lines",
    "cnc_sheet_plans",
    "cnc_parts",
    "cnc_programs",
    "cnc_tools",
    "cnc_machines",
]

CNC_PERMISSIONS = {
    "cnc.create": ("CNC create", "General CNC create access", "cnc"),
    "cnc.edit": ("CNC edit", "General CNC edit access", "cnc"),
    "cnc.execute": ("CNC execute", "General CNC execution access", "cnc"),
    "cnc.approve": ("CNC approve", "General CNC approval access", "cnc"),
    "cnc.read": ("ЧПК", "Перегляд модуля ЧПК", "cnc"),
    "cnc.work_orders.create": ("Створення завдань ЧПК", "Створення завдань ЧПК", "cnc"),
    "cnc.work_orders.edit": ("Редагування завдань ЧПК", "Редагування завдань ЧПК", "cnc"),
    "cnc.work_orders.plan": ("Планування ЧПК", "Планування карт розкрою та завдань", "cnc"),
    "cnc.work_orders.queue": ("Черга ЧПК", "Керування чергою ЧПК", "cnc"),
    "cnc.work_orders.start": ("Запуск ЧПК", "Початок налаштування та обробки", "cnc"),
    "cnc.work_orders.pause": ("Пауза ЧПК", "Пауза та продовження ЧПК", "cnc"),
    "cnc.work_orders.complete": ("Завершення ЧПК", "Випуск і завершення завдань", "cnc"),
    "cnc.work_orders.cancel": ("Скасування ЧПК", "Скасування завдань ЧПК", "cnc"),
    "cnc.materials.read": ("Матеріали ЧПК", "Перегляд матеріалів ЧПК", "cnc"),
    "cnc.materials.issue": ("Видача матеріалів ЧПК", "Видача матеріалів у ЧПК", "cnc"),
    "cnc.materials.return": ("Повернення матеріалів ЧПК", "Повернення матеріалів з ЧПК", "cnc"),
    "cnc.materials.scrap": ("Списання матеріалів ЧПК", "Брак і списання матеріалів ЧПК", "cnc"),
    "cnc.output.post": ("Оприбуткування ЧПК", "Оприбуткування готових деталей ЧПК", "cnc"),
    "cnc.offcuts.manage": ("Залишки ЧПК", "Керування придатними залишками ЧПК", "cnc"),
    "cnc.machines.read": ("Верстати ЧПК", "Перегляд верстатів ЧПК", "cnc"),
    "cnc.machines.manage": ("Керування верстатами ЧПК", "Створення та зміна верстатів", "cnc"),
    "cnc.programs.read": ("Програми ЧПК", "Перегляд програм ЧПК", "cnc"),
    "cnc.programs.manage": ("Керування програмами ЧПК", "Ревізії та затвердження програм", "cnc"),
    "cnc.tools.read": ("Інструмент ЧПК", "Перегляд інструменту ЧПК", "cnc"),
    "cnc.tools.manage": ("Керування інструментом ЧПК", "Створення та зміна інструменту", "cnc"),
    "cnc.settings.manage": ("Налаштування ЧПК", "Керування налаштуваннями ЧПК", "cnc"),
    "cnc.export": ("Експорт ЧПК", "PDF, XLSX і друк завдань ЧПК", "cnc"),
    "cnc.audit.read": ("Аудит ЧПК", "Перегляд аудиту ЧПК", "cnc"),
}

CNC_ROLES = {
    "cnc_operator": (
        "Оператор ЧПК",
        "Операторський доступ до виконання завдань ЧПК.",
        [
            "cnc.read",
            "cnc.execute",
            "cnc.work_orders.start",
            "cnc.work_orders.pause",
            "cnc.work_orders.complete",
            "cnc.materials.read",
            "cnc.tools.read",
            "cnc.programs.read",
        ],
    ),
    "cnc_shop_lead": (
        "Майстер дільниці ЧПК",
        "Операційне керування чергою, матеріалами та випуском ЧПК.",
        list(CNC_PERMISSIONS),
    ),
    "cnc_technologist": (
        "Технолог ЧПК",
        "Керування деталями, програмами, інструментом та картами розкрою.",
        [
            "cnc.read",
            "cnc.approve",
            "cnc.work_orders.plan",
            "cnc.programs.read",
            "cnc.programs.manage",
            "cnc.tools.read",
            "cnc.tools.manage",
            "cnc.export",
        ],
    ),
    "cnc_viewer": (
        "Перегляд ЧПК",
        "Перегляд завдань, черги та документів ЧПК без змін.",
        ["cnc.read", "cnc.machines.read", "cnc.programs.read", "cnc.tools.read", "cnc.export"],
    ),
}


def upgrade() -> None:
    bind = op.get_bind()
    for table in CNC_TABLES:
        table.create(bind=bind, checkfirst=True)
    _seed_access()


def downgrade() -> None:
    for table_name in CNC_TABLE_NAMES_DOWNGRADE:
        op.drop_table(table_name, if_exists=True)
    op.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id IN "
            "(SELECT id FROM permissions WHERE code LIKE 'cnc.%')"
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code LIKE 'cnc.%'"))


def _seed_access() -> None:
    for code, (name, description, module) in CNC_PERMISSIONS.items():
        op.execute(
            sa.text(
                "INSERT INTO permissions (id, code, name, description, module, is_active) "
                "VALUES (gen_random_uuid(), :code, :name, :description, :module, true) "
                "ON CONFLICT (code) DO UPDATE SET name = EXCLUDED.name, "
                "description = EXCLUDED.description, module = EXCLUDED.module, is_active = true"
            ).bindparams(code=code, name=name, description=description, module=module)
        )
    for code, (name, description, permission_codes) in CNC_ROLES.items():
        op.execute(
            sa.text(
                "INSERT INTO roles (id, name, code, description, is_system, is_active, "
                "created_at, updated_at, version) "
                "VALUES (gen_random_uuid(), :name, :code, :description, true, true, "
                "now(), now(), 1) "
                "ON CONFLICT (code) DO NOTHING"
            ).bindparams(code=code, name=name, description=description)
        )
        for permission_code in permission_codes:
            op.execute(
                sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) "
                    "SELECT gen_random_uuid(), r.id, p.id FROM roles r CROSS JOIN permissions p "
                    "WHERE r.code = :role_code AND p.code = :permission_code "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ).bindparams(role_code=code, permission_code=permission_code)
            )
    for role_code in ("system_admin", "production_manager"):
        for permission_code in CNC_PERMISSIONS:
            op.execute(
                sa.text(
                    "INSERT INTO role_permissions (id, role_id, permission_id) "
                    "SELECT gen_random_uuid(), r.id, p.id FROM roles r CROSS JOIN permissions p "
                    "WHERE r.code = :role_code AND p.code = :permission_code "
                    "ON CONFLICT (role_id, permission_id) DO NOTHING"
                ).bindparams(role_code=role_code, permission_code=permission_code)
            )
