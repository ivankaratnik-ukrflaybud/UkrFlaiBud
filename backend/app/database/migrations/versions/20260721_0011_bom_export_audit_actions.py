"""Allow BOM export audit actions.

Revision ID: 20260721_0011
Revises: 20260720_0010
Create Date: 2026-07-21 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260721_0011"
down_revision: str | None = "20260720_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

AUDIT_ACTIONS = (
    "create",
    "update",
    "delete",
    "restore",
    "system",
    "export_pdf",
    "export_xlsx",
)
LEGACY_AUDIT_ACTIONS = ("create", "update", "delete", "restore", "system")


def upgrade() -> None:
    _replace_audit_action_constraint(AUDIT_ACTIONS)


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE audit_log SET action = 'system' "
            "WHERE action IN ('export_pdf', 'export_xlsx')"
        )
    )
    _replace_audit_action_constraint(LEGACY_AUDIT_ACTIONS)


def _replace_audit_action_constraint(actions: tuple[str, ...]) -> None:
    op.drop_constraint("ck_audit_log_action", "audit_log", type_="check")
    allowed_values = ", ".join(f"'{action}'" for action in actions)
    op.create_check_constraint(
        "ck_audit_log_action",
        "audit_log",
        f"action IN ({allowed_values})",
    )
