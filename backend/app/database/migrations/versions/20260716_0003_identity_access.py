"""Identity and access module.

Revision ID: 20260716_0003
Revises: 20260716_0002
Create Date: 2026-07-16 01:00:00.000000

"""

from collections.abc import Sequence
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260716_0003"
down_revision: str | None = "20260716_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PERMISSIONS = {
    "organizations.read": ("Організації", "Перегляд організацій", "organizations"),
    "organizations.manage": (
        "Керування організаціями",
        "Створення та редагування організацій",
        "organizations",
    ),
    "departments.read": ("Підрозділи", "Перегляд підрозділів", "organizations"),
    "departments.manage": (
        "Керування підрозділами",
        "Створення та редагування підрозділів",
        "organizations",
    ),
    "positions.read": ("Посади", "Перегляд посад", "organizations"),
    "positions.manage": ("Керування посадами", "Створення та редагування посад", "organizations"),
    "employees.read": ("Працівники", "Перегляд працівників", "organizations"),
    "employees.manage": (
        "Керування працівниками",
        "Створення та редагування працівників",
        "organizations",
    ),
    "users.read": ("Користувачі", "Перегляд користувачів", "identity"),
    "users.manage": (
        "Керування користувачами",
        "Створення та редагування користувачів",
        "identity",
    ),
    "roles.read": ("Ролі", "Перегляд ролей", "identity"),
    "roles.manage": ("Керування ролями", "Редагування ролей та доступу", "identity"),
    "sessions.manage": ("Сеанси", "Керування активними пристроями", "identity"),
    "audit.read": ("Журнал дій", "Перегляд журналу дій", "audit"),
    "settings.manage": ("Налаштування", "Керування налаштуваннями", "settings"),
}

ROLE_TEMPLATES = {
    "system_admin": ("Системний адміністратор", "Повний доступ до системи.", list(PERMISSIONS)),
    "director": (
        "Директор",
        "Повний робочий доступ, користувачі, ролі та журнал дій.",
        [code for code in PERMISSIONS if code != "settings.manage"],
    ),
    "department_manager": (
        "Керівник підрозділу",
        "Перегляд структури та базове керування працівниками.",
        [
            "organizations.read",
            "departments.read",
            "positions.read",
            "employees.read",
            "employees.manage",
        ],
    ),
    "employee": (
        "Працівник",
        "Базовий перегляд організаційної інформації.",
        ["organizations.read", "departments.read", "positions.read", "employees.read"],
    ),
    "viewer": (
        "Перегляд",
        "Тільки перегляд без змін.",
        [
            "organizations.read",
            "departments.read",
            "positions.read",
            "employees.read",
            "users.read",
            "roles.read",
        ],
    ),
}


def entity_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        *entity_columns(),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("normalized_email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_superuser", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("must_change_password", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["employee_id"], ["employees.id"], name="fk_users_employee_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("normalized_email", name="uq_users_normalized_email"),
    )
    op.create_index(
        "ix_users_employee_id_active",
        "users",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_locked_until", "users", ["locked_until"])

    op.create_table(
        "roles",
        *entity_columns(),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_roles"),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_is_active", "roles", ["is_active"])
    op.create_index("ix_roles_is_system", "roles", ["is_system"])

    op.create_table(
        "permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("module", sa.String(length=80), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_permissions"),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_module", "permissions", ["module"])

    op.create_table(
        "user_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            name="fk_user_roles_organization_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_user_roles_role_id", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_roles_user_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_roles"),
        sa.UniqueConstraint("user_id", "role_id", "organization_id", name="uq_user_roles_scope"),
    )
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_index("ix_user_roles_user_id", "user_roles", ["user_id"])

    op.create_table(
        "role_permissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            ["permissions.id"],
            name="fk_role_permissions_permission_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], ["roles.id"], name="fk_role_permissions_role_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_role_permissions"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("refresh_token_hash", sa.String(length=255), nullable=False),
        sa.Column("device_name", sa.String(length=160), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.String(length=160), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_user_sessions_user_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_user_sessions"),
    )
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"])
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"])
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"])

    op.create_table(
        "login_attempts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("failure_reason", sa.String(length=160), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_login_attempts_user_id", ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_login_attempts"),
    )
    op.create_index("ix_login_attempts_created_at", "login_attempts", ["created_at"])
    op.create_index("ix_login_attempts_email", "login_attempts", ["email"])
    op.create_index("ix_login_attempts_user_id", "login_attempts", ["user_id"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name="fk_password_reset_tokens_user_id", ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_password_reset_tokens"),
    )
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    seed_system_access()


def seed_system_access() -> None:
    permissions_table = sa.table(
        "permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("module", sa.String()),
        sa.column("is_active", sa.Boolean()),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("name", sa.String()),
        sa.column("code", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("role_id", postgresql.UUID(as_uuid=True)),
        sa.column("permission_id", postgresql.UUID(as_uuid=True)),
    )
    permission_ids = {code: uuid4() for code in PERMISSIONS}
    role_ids = {code: uuid4() for code in ROLE_TEMPLATES}
    op.bulk_insert(
        permissions_table,
        [
            {
                "id": permission_ids[code],
                "code": code,
                "name": name,
                "description": description,
                "module": module,
                "is_active": True,
            }
            for code, (name, description, module) in PERMISSIONS.items()
        ],
    )
    op.bulk_insert(
        roles_table,
        [
            {
                "id": role_ids[code],
                "name": name,
                "code": code,
                "description": description,
                "is_system": True,
                "is_active": True,
            }
            for code, (name, description, _) in ROLE_TEMPLATES.items()
        ],
    )
    op.bulk_insert(
        role_permissions_table,
        [
            {
                "id": uuid4(),
                "role_id": role_ids[role_code],
                "permission_id": permission_ids[permission_code],
            }
            for role_code, (_, _, permission_codes) in ROLE_TEMPLATES.items()
            for permission_code in permission_codes
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_index("ix_login_attempts_user_id", table_name="login_attempts")
    op.drop_index("ix_login_attempts_email", table_name="login_attempts")
    op.drop_index("ix_login_attempts_created_at", table_name="login_attempts")
    op.drop_table("login_attempts")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_user_sessions_revoked_at", table_name="user_sessions")
    op.drop_index("ix_user_sessions_expires_at", table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_table("role_permissions")
    op.drop_index("ix_user_roles_user_id", table_name="user_roles")
    op.drop_index("ix_user_roles_role_id", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_index("ix_permissions_module", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_is_system", table_name="roles")
    op.drop_index("ix_roles_is_active", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_users_locked_until", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_employee_id_active", table_name="users")
    op.drop_table("users")
