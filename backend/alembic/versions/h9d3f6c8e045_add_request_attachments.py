"""Add request attachment metadata.

Revision ID: h9d3f6c8e045
Revises: g8c2e5b7d934
"""
import sqlalchemy as sa
from alembic import op

revision = "h9d3f6c8e045"
down_revision = "g8c2e5b7d934"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "request_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("object_key", sa.String(512), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(160), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=True),
        sa.Column("visibility", sa.String(24), nullable=False, server_default="REQUESTER_VISIBLE"),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("storage_etag", sa.Text(), nullable=True),
        sa.UniqueConstraint("object_key", name="uq_request_attachments_object_key"),
        sa.CheckConstraint(
            "status IN ('PENDING','READY','QUARANTINED','DELETED')",
            name="ck_request_attachment_status",
        ),
        sa.CheckConstraint(
            "visibility IN ('REQUESTER_VISIBLE','INTERNAL')",
            name="ck_request_attachment_visibility",
        ),
    )
    op.create_index("ix_request_attachments_request_id", "request_attachments", ["request_id"])
    op.create_index("ix_request_attachments_uploaded_by", "request_attachments", ["uploaded_by"])
    op.create_index("ix_request_attachments_status", "request_attachments", ["status"])
    op.create_index(
        "ix_request_attachments_request_status",
        "request_attachments",
        ["request_id", "status"],
    )


def downgrade():
    bind = op.get_bind()
    ready_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM request_attachments WHERE status IN ('READY','QUARANTINED')")
    ).scalar_one()
    if ready_count:
        raise RuntimeError(
            "Refusing downgrade: uploaded attachment metadata would be lost while objects may remain in storage"
        )
    op.drop_index("ix_request_attachments_request_status", table_name="request_attachments")
    op.drop_index("ix_request_attachments_status", table_name="request_attachments")
    op.drop_index("ix_request_attachments_uploaded_by", table_name="request_attachments")
    op.drop_index("ix_request_attachments_request_id", table_name="request_attachments")
    op.drop_table("request_attachments")
