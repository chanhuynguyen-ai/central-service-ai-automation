"""add organization rbac foundation

Revision ID: 7d9b2f3a4c11
Revises: 05269d4b0748
Create Date: 2026-09-04

"""

from collections.abc import Sequence
from datetime import UTC, datetime
import re

from alembic import op
import sqlalchemy as sa


revision: str = "7d9b2f3a4c11"
down_revision: str | Sequence[str] | None = "05269d4b0748"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SYSTEM_ROLES = (
    (
        "EMPLOYEE",
        "Employee",
        "Standard employee who creates and follows service requests.",
    ),
    (
        "APPROVER",
        "Approver",
        "User allowed to act on assigned approval tasks.",
    ),
    (
        "MANAGER",
        "Manager",
        "Line manager who may participate in manager approval workflows.",
    ),
    (
        "SERVICE_AGENT",
        "Service Agent",
        "Agent responsible for fulfilling service work.",
    ),
    (
        "SERVICE_LEAD",
        "Service Lead",
        "Lead responsible for a service team and escalated work.",
    ),
    (
        "ADMIN",
        "Administrator",
        "System administrator with privileged configuration access.",
    ),
    (
        "AUDITOR",
        "Auditor",
        "Read-oriented role for audit and governance activities.",
    ),
)


def _department_code(name: str, used_codes: set[str]) -> str:
    base = re.sub(r"[^A-Z0-9]+", "_", name.strip().upper()).strip("_")
    if not base:
        base = "DEPARTMENT"

    base = base[:50]
    candidate = base
    suffix = 2

    while candidate in used_codes:
        suffix_text = f"_{suffix}"
        candidate = f"{base[: 50 - len(suffix_text)]}{suffix_text}"
        suffix += 1

    used_codes.add(candidate)
    return candidate


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_departments_code",
        "departments",
        ["code"],
        unique=True,
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_roles_code",
        "roles",
        ["code"],
        unique=True,
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "department_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "manager_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_users_department_id",
            ["department_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_users_manager_id",
            ["manager_id"],
            unique=False,
        )
        batch_op.create_foreign_key(
            "fk_users_department_id_departments",
            "departments",
            ["department_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_users_manager_id_users",
            "users",
            ["manager_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name="fk_user_roles_role_id_roles",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_user_roles_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id"),
    )

    op.create_table(
        "service_teams",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("lead_user_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_service_teams_department_id_departments",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["lead_user_id"],
            ["users.id"],
            name="fk_service_teams_lead_user_id_users",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_service_teams_code",
        "service_teams",
        ["code"],
        unique=True,
    )
    op.create_index(
        "ix_service_teams_department_id",
        "service_teams",
        ["department_id"],
        unique=False,
    )
    op.create_index(
        "ix_service_teams_lead_user_id",
        "service_teams",
        ["lead_user_id"],
        unique=False,
    )

    op.create_table(
        "service_team_members",
        sa.Column("service_team_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["service_team_id"],
            ["service_teams.id"],
            name="fk_service_team_members_team_id_service_teams",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_service_team_members_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "service_team_id",
            "user_id",
        ),
    )

    _backfill_legacy_organization_data()


def _backfill_legacy_organization_data() -> None:
    bind = op.get_bind()
    now = datetime.now(UTC)

    departments = sa.table(
        "departments",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    roles = sa.table(
        "roles",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )

    users = sa.table(
        "users",
        sa.column("id", sa.Integer()),
        sa.column("department", sa.String()),
        sa.column("role", sa.String()),
        sa.column("department_id", sa.Integer()),
    )

    user_roles = sa.table(
        "user_roles",
        sa.column("user_id", sa.Integer()),
        sa.column("role_id", sa.Integer()),
        sa.column("assigned_at", sa.DateTime(timezone=True)),
    )

    for code, name, description in SYSTEM_ROLES:
        bind.execute(
            roles.insert().values(
                code=code,
                name=name,
                description=description,
                is_system=True,
                created_at=now,
            )
        )

    user_rows = bind.execute(
        sa.select(
            users.c.id,
            users.c.department,
            users.c.role,
        )
    ).mappings().all()

    department_names = sorted(
        {
            row["department"].strip()
            for row in user_rows
            if row["department"] and row["department"].strip()
        }
    )

    used_codes: set[str] = set()

    for department_name in department_names:
        bind.execute(
            departments.insert().values(
                code=_department_code(
                    department_name,
                    used_codes,
                ),
                name=department_name,
                is_active=True,
                created_at=now,
            )
        )

    department_rows = bind.execute(
        sa.select(
            departments.c.id,
            departments.c.name,
        )
    ).mappings().all()

    department_ids = {
        row["name"]: row["id"]
        for row in department_rows
    }

    role_rows = bind.execute(
        sa.select(
            roles.c.id,
            roles.c.code,
        )
    ).mappings().all()

    role_ids = {
        row["code"]: row["id"]
        for row in role_rows
    }

    legacy_role_codes = {
        row["role"].strip().upper()
        for row in user_rows
        if row["role"] and row["role"].strip()
    }

    for role_code in sorted(legacy_role_codes):
        if role_code in role_ids:
            continue

        role_name = role_code.replace("_", " ").title()

        result = bind.execute(
            roles.insert().values(
                code=role_code,
                name=role_name,
                description="Role migrated from the legacy prototype model.",
                is_system=False,
                created_at=now,
            )
        )

        role_ids[role_code] = result.inserted_primary_key[0]

    for row in user_rows:
        department_name = (
            row["department"].strip()
            if row["department"]
            else ""
        )

        department_id = department_ids.get(department_name)

        if department_id is not None:
            bind.execute(
                users.update()
                .where(users.c.id == row["id"])
                .values(department_id=department_id)
            )

        role_code = (
            row["role"].strip().upper()
            if row["role"]
            else ""
        )

        role_id = role_ids.get(role_code)

        if role_id is not None:
            bind.execute(
                user_roles.insert().values(
                    user_id=row["id"],
                    role_id=role_id,
                    assigned_at=now,
                )
            )


def downgrade() -> None:
    op.drop_table("service_team_members")

    op.drop_index(
        "ix_service_teams_lead_user_id",
        table_name="service_teams",
    )
    op.drop_index(
        "ix_service_teams_department_id",
        table_name="service_teams",
    )
    op.drop_index(
        "ix_service_teams_code",
        table_name="service_teams",
    )
    op.drop_table("service_teams")

    op.drop_table("user_roles")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(
            "fk_users_manager_id_users",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_users_department_id_departments",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_users_manager_id")
        batch_op.drop_index("ix_users_department_id")
        batch_op.drop_column("manager_id")
        batch_op.drop_column("department_id")

    op.drop_index(
        "ix_roles_code",
        table_name="roles",
    )
    op.drop_table("roles")

    op.drop_index(
        "ix_departments_code",
        table_name="departments",
    )
    op.drop_table("departments")