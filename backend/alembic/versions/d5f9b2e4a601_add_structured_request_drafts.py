"""Add structured draft fields to the existing request aggregate.

Revision ID: d5f9b2e4a601
Revises: c4e8a1d2f730
"""
from alembic import op
import sqlalchemy as sa

revision = "d5f9b2e4a601"
down_revision = "c4e8a1d2f730"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_request_type_one_published", "request_type_versions", ["request_type_id"],
        unique=True, sqlite_where=sa.text("status = 'PUBLISHED'"),
        postgresql_where=sa.text("status = 'PUBLISHED'"),
    )
    with op.batch_alter_table("service_requests") as batch:
        batch.add_column(sa.Column("request_type_version_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("form_data", sa.JSON(), nullable=False, server_default="{}"))
        batch.add_column(sa.Column("draft_revision", sa.Integer(), nullable=False, server_default="1"))
        batch.create_foreign_key(
            "fk_service_requests_request_type_version_id", "request_type_versions",
            ["request_type_version_id"], ["id"], ondelete="RESTRICT",
        )
        batch.create_index("ix_service_requests_request_type_version_id", ["request_type_version_id"])
        batch.alter_column("submitted_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.alter_column("due_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.alter_column("category", existing_type=sa.String(60), type_=sa.String(80), existing_nullable=False)


def downgrade() -> None:
    connection = op.get_bind()
    count = connection.execute(sa.text(
        "SELECT COUNT(*) FROM service_requests WHERE request_type_version_id IS NOT NULL "
        "OR submitted_at IS NULL OR due_at IS NULL OR length(category) > 60"
    )).scalar_one()
    if count:
        raise RuntimeError("Cannot downgrade while structured draft data exists; export/migrate it first.")
    op.drop_index("uq_request_type_one_published", table_name="request_type_versions")
    with op.batch_alter_table("service_requests") as batch:
        batch.drop_index("ix_service_requests_request_type_version_id")
        batch.drop_constraint("fk_service_requests_request_type_version_id", type_="foreignkey")
        batch.drop_column("draft_revision")
        batch.drop_column("form_data")
        batch.drop_column("request_type_version_id")
        batch.alter_column("submitted_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column("due_at", existing_type=sa.DateTime(timezone=True), nullable=False)
        batch.alter_column("category", existing_type=sa.String(80), type_=sa.String(60), existing_nullable=False)
