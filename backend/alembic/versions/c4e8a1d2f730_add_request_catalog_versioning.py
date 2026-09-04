"""add request catalog versioning

Revision ID: c4e8a1d2f730
Revises: 9c1a4f6b2d80
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8a1d2f730"
down_revision: str | None = "9c1a4f6b2d80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "request_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("owner_service_team_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["owner_service_team_id"],
            ["service_teams.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("code", name="uq_request_types_code"),
    )
    op.create_index("ix_request_types_code", "request_types", ["code"], unique=True)
    op.create_index("ix_request_types_category", "request_types", ["category"], unique=False)
    op.create_index(
        "ix_request_types_owner_service_team_id",
        "request_types",
        ["owner_service_team_id"],
        unique=False,
    )
    op.create_index("ix_request_types_is_active", "request_types", ["is_active"], unique=False)

    op.create_table(
        "request_type_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_type_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=180), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("form_schema", sa.JSON(), nullable=False),
        sa.Column("validation_schema", sa.JSON(), nullable=True),
        sa.Column("sla_config", sa.JSON(), nullable=True),
        sa.Column("attachment_config", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="DRAFT"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["request_type_id"],
            ["request_types.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "request_type_id",
            "version",
            name="uq_request_type_version",
        ),
    )
    op.create_index(
        "ix_request_type_versions_request_type_id",
        "request_type_versions",
        ["request_type_id"],
        unique=False,
    )
    op.create_index(
        "ix_request_type_versions_status",
        "request_type_versions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_request_type_versions_created_by",
        "request_type_versions",
        ["created_by"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_request_type_versions_created_by", table_name="request_type_versions")
    op.drop_index("ix_request_type_versions_status", table_name="request_type_versions")
    op.drop_index("ix_request_type_versions_request_type_id", table_name="request_type_versions")
    op.drop_table("request_type_versions")

    op.drop_index("ix_request_types_is_active", table_name="request_types")
    op.drop_index("ix_request_types_owner_service_team_id", table_name="request_types")
    op.drop_index("ix_request_types_category", table_name="request_types")
    op.drop_index("ix_request_types_code", table_name="request_types")
    op.drop_table("request_types")
