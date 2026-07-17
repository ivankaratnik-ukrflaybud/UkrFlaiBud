"""Remove smoke-test inventory and demo organization data.

Revision ID: 20260717_0008
Revises: 20260717_0007
Create Date: 2026-07-17 19:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260717_0008"
down_revision: str | None = "20260717_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    create_cleanup_maps(bind)
    normalize_seed_owner(bind)
    delete_demo_inventory(bind)
    rehome_seed_references(bind)
    delete_demo_identity_and_organizations(bind)
    delete_demo_audit_and_outbox(bind)


def downgrade() -> None:
    pass


def create_cleanup_maps(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_seed_org ON COMMIT DROP AS
            SELECT organization.id
            FROM organizations organization
            LEFT JOIN inventory_sites site ON site.organization_id = organization.id
            ORDER BY
                (site.code = 'KYIV') DESC,
                (
                    organization.name ILIKE '%smoke%'
                    OR organization.name ILIKE '%reversal%'
                    OR organization.short_name ILIKE 'SM%'
                    OR organization.short_name ILIKE 'S5-%'
                    OR organization.short_name ILIKE 'REV-%'
                ) ASC,
                organization.created_at ASC,
                organization.id ASC
            LIMIT 1
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_items ON COMMIT DROP AS
            SELECT id
            FROM inventory_items
            WHERE sku LIKE 'SMOKE-%'
               OR sku LIKE 'REV-%'
               OR name = 'Reversal item'
               OR name ~ '\\?{2,}.*smoke'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_documents ON COMMIT DROP AS
            SELECT document.id
            FROM inventory_documents document
            JOIN inventory_document_lines line ON line.document_id = document.id
            GROUP BY document.id
            HAVING count(*) = count(*) FILTER (
                WHERE line.item_id IN (SELECT id FROM production_cleanup_items)
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_lines ON COMMIT DROP AS
            SELECT line.id
            FROM inventory_document_lines line
            WHERE line.item_id IN (SELECT id FROM production_cleanup_items)
               OR line.document_id IN (SELECT id FROM production_cleanup_documents)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_movements ON COMMIT DROP AS
            SELECT movement.id
            FROM inventory_movements movement
            WHERE movement.item_id IN (SELECT id FROM production_cleanup_items)
               OR movement.document_id IN (SELECT id FROM production_cleanup_documents)
               OR movement.document_line_id IN (SELECT id FROM production_cleanup_lines)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_lots ON COMMIT DROP AS
            SELECT id
            FROM inventory_lots
            WHERE item_id IN (SELECT id FROM production_cleanup_items)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_serials ON COMMIT DROP AS
            SELECT id
            FROM inventory_serials
            WHERE item_id IN (SELECT id FROM production_cleanup_items)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_locations ON COMMIT DROP AS
            SELECT location.id
            FROM inventory_storage_locations location
            WHERE location.name ~ '\\?{2,}'
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_stock_balances balance
                  WHERE balance.location_id = location.id
                    AND balance.item_id NOT IN (SELECT id FROM production_cleanup_items)
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_movements movement
                  WHERE movement.location_id = location.id
                    AND movement.id NOT IN (SELECT id FROM production_cleanup_movements)
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_serials serial
                  WHERE serial.current_location_id = location.id
                    AND serial.id NOT IN (SELECT id FROM production_cleanup_serials)
              )
              AND NOT EXISTS (
                  SELECT 1
                  FROM inventory_document_lines line
                  WHERE (
                        line.source_location_id = location.id
                        OR line.destination_location_id = location.id
                    )
                    AND line.id NOT IN (SELECT id FROM production_cleanup_lines)
              )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_categories ON COMMIT DROP AS
            SELECT category.id
            FROM inventory_item_categories category
            WHERE category.code = 'REV'
               OR category.name = 'Reversal category'
               OR (
                    category.name ~ '^\\?+$'
                    AND NOT EXISTS (
                        SELECT 1
                        FROM inventory_items item
                        WHERE item.category_id = category.id
                          AND item.id NOT IN (SELECT id FROM production_cleanup_items)
                    )
               )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_users ON COMMIT DROP AS
            SELECT id
            FROM users
            WHERE email ILIKE 'smoke-%'
               OR email ILIKE 'restricted%'
               OR display_name ILIKE '%smoke%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_organizations ON COMMIT DROP AS
            SELECT id
            FROM organizations
            WHERE id NOT IN (SELECT id FROM production_seed_org)
              AND (
                    name ILIKE '%smoke%'
                    OR name ILIKE '%reversal%'
                    OR short_name ILIKE 'SM%'
                    OR short_name ILIKE 'S5-%'
                    OR short_name ILIKE 'REV-%'
              )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_employees ON COMMIT DROP AS
            SELECT employee.id
            FROM employees employee
            WHERE employee.organization_id IN (SELECT id FROM production_cleanup_organizations)
               OR (
                    employee.first_name ILIKE '%smoke%'
                    AND employee.last_name ILIKE '%user%'
               )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_positions ON COMMIT DROP AS
            SELECT position.id
            FROM positions position
            WHERE position.organization_id IN (SELECT id FROM production_cleanup_organizations)
               OR position.name ILIKE '%smoke%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            CREATE TEMP TABLE production_cleanup_departments ON COMMIT DROP AS
            SELECT department.id
            FROM departments department
            WHERE department.organization_id IN (SELECT id FROM production_cleanup_organizations)
               OR department.name ILIKE '%smoke%'
            """
        )
    )


def normalize_seed_owner(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE organizations organization
            SET
                name = 'UKRFLYBUD',
                short_name = 'UKRFLYBUD',
                legal_name = 'UKRFLYBUD',
                updated_at = now(),
                version = organization.version + 1
            FROM production_seed_org seed_org
            WHERE organization.id = seed_org.id
              AND (
                    organization.name ILIKE '%smoke%'
                    OR organization.name ILIKE '%reversal%'
                    OR organization.short_name ILIKE 'SM%'
                    OR organization.short_name ILIKE 'S5-%'
                    OR organization.short_name ILIKE 'REV-%'
              )
            """
        )
    )


def delete_demo_inventory(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            UPDATE inventory_movements movement
            SET reversal_of_movement_id = NULL
            WHERE movement.reversal_of_movement_id IN (
                SELECT id FROM production_cleanup_movements
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_document_line_serials line_serial
            WHERE line_serial.line_id IN (SELECT id FROM production_cleanup_lines)
               OR line_serial.serial_id IN (SELECT id FROM production_cleanup_serials)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_movements movement
            WHERE movement.id IN (SELECT id FROM production_cleanup_movements)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_stock_balances balance
            WHERE balance.item_id IN (SELECT id FROM production_cleanup_items)
               OR balance.location_id IN (SELECT id FROM production_cleanup_locations)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_serials serial
            WHERE serial.id IN (SELECT id FROM production_cleanup_serials)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_lots lot
            WHERE lot.id IN (SELECT id FROM production_cleanup_lots)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_document_lines line
            WHERE line.id IN (SELECT id FROM production_cleanup_lines)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_documents document
            WHERE document.id IN (SELECT id FROM production_cleanup_documents)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_items item
            WHERE item.id IN (SELECT id FROM production_cleanup_items)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_storage_locations location
            WHERE location.id IN (SELECT id FROM production_cleanup_locations)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM inventory_item_categories category
            WHERE category.id IN (SELECT id FROM production_cleanup_categories)
            """
        )
    )


def rehome_seed_references(bind: sa.Connection) -> None:
    for table_name, code_filter in (
        ("inventory_sites", "code IN ('KYIV', 'TALNE')"),
        ("inventory_warehouses", "code IN ('KYIV-MAIN', 'TALNE-MAIN')"),
        ("inventory_units", "code IN ('PCS', 'SET', 'M', 'M2', 'KG', 'G', 'L', 'PACK')"),
        ("inventory_item_categories", "code = 'ELEC'"),
    ):
        bind.execute(
            sa.text(
                f"""
                UPDATE {table_name} target
                SET
                    organization_id = seed_org.id,
                    updated_at = now(),
                    version = target.version + 1
                FROM production_seed_org seed_org
                WHERE {code_filter}
                  AND target.organization_id <> seed_org.id
                """
            )
        )
    bind.execute(
        sa.text(
            """
            UPDATE inventory_storage_locations location
            SET
                organization_id = seed_org.id,
                updated_at = now(),
                version = location.version + 1
            FROM production_seed_org seed_org
            JOIN inventory_warehouses warehouse ON warehouse.organization_id = seed_org.id
            WHERE location.warehouse_id = warehouse.id
              AND location.organization_id <> seed_org.id
            """
        )
    )


def delete_demo_identity_and_organizations(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM login_attempts attempt
            WHERE attempt.user_id IN (SELECT id FROM production_cleanup_users)
               OR attempt.email ILIKE 'smoke-%'
               OR attempt.email ILIKE 'restricted%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM user_sessions session
            WHERE session.user_id IN (SELECT id FROM production_cleanup_users)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM password_reset_tokens token
            WHERE token.user_id IN (SELECT id FROM production_cleanup_users)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM user_roles user_role
            WHERE user_role.user_id IN (SELECT id FROM production_cleanup_users)
               OR user_role.organization_id IN (SELECT id FROM production_cleanup_organizations)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM users user_account
            WHERE user_account.id IN (SELECT id FROM production_cleanup_users)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE employees employee
            SET supervisor_employee_id = NULL
            WHERE employee.supervisor_employee_id IN (
                SELECT id FROM production_cleanup_employees
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE departments department
            SET parent_department_id = NULL
            WHERE department.parent_department_id IN (
                SELECT id FROM production_cleanup_departments
            )
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM employees employee
            WHERE employee.id IN (SELECT id FROM production_cleanup_employees)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM positions position
            WHERE position.id IN (SELECT id FROM production_cleanup_positions)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM departments department
            WHERE department.id IN (SELECT id FROM production_cleanup_departments)
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM organizations organization
            WHERE organization.id IN (SELECT id FROM production_cleanup_organizations)
            """
        )
    )


def delete_demo_audit_and_outbox(bind: sa.Connection) -> None:
    bind.execute(
        sa.text(
            """
            DELETE FROM outbox_event event
            WHERE event.aggregate_id IN (SELECT id FROM production_cleanup_items)
               OR event.aggregate_id IN (SELECT id FROM production_cleanup_documents)
               OR event.payload::text ILIKE '%SMOKE-%'
               OR event.payload::text ILIKE '%REV-%'
               OR event.payload::text ILIKE '%Reversal%'
               OR event.payload::text LIKE '%????%'
            """
        )
    )
    bind.execute(
        sa.text(
            """
            DELETE FROM audit_log audit
            WHERE audit.actor_id IN (SELECT id FROM production_cleanup_users)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_items)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_documents)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_categories)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_locations)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_users)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_organizations)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_employees)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_positions)
               OR audit.entity_id IN (SELECT id FROM production_cleanup_departments)
               OR audit.before_data::text ILIKE '%SMOKE-%'
               OR audit.after_data::text ILIKE '%SMOKE-%'
               OR audit.before_data::text ILIKE '%REV-%'
               OR audit.after_data::text ILIKE '%REV-%'
               OR audit.before_data::text ILIKE '%Reversal%'
               OR audit.after_data::text ILIKE '%Reversal%'
               OR audit.before_data::text LIKE '%????%'
               OR audit.after_data::text LIKE '%????%'
            """
        )
    )
