"""Add durable in-app and email notifications.

Revision ID: i0e4g7d9f156
Revises: h9d3f6c8e045
"""

import sqlalchemy as sa
from alembic import op

revision = "i0e4g7d9f156"
down_revision = "h9d3f6c8e045"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("recipient_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("service_requests.id", ondelete="CASCADE"), nullable=True),
        sa.Column("event_key", sa.String(180), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("channel", sa.String(20), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_key", "channel", name="uq_notification_event_channel"),
        sa.CheckConstraint("channel IN ('IN_APP','EMAIL')", name="ck_notification_channel"),
        sa.CheckConstraint("status IN ('PENDING','SENT','FAILED','DEAD','READ')", name="ck_notification_status"),
    )
    op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
    op.create_index("ix_notifications_request_id", "notifications", ["request_id"])
    op.create_index("ix_notifications_kind", "notifications", ["kind"])
    op.create_index("ix_notifications_channel", "notifications", ["channel"])
    op.create_index("ix_notifications_status", "notifications", ["status"])
    op.create_index("ix_notifications_available_at", "notifications", ["available_at"])
    op.create_index(
        "ix_notifications_recipient_channel_read",
        "notifications",
        ["recipient_user_id", "channel", "read_at"],
    )


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM notifications")).scalar_one()
    if count:
        raise RuntimeError("Refusing downgrade: notification history would be lost")
    op.drop_index("ix_notifications_recipient_channel_read", table_name="notifications")
    op.drop_index("ix_notifications_available_at", table_name="notifications")
    op.drop_index("ix_notifications_status", table_name="notifications")
    op.drop_index("ix_notifications_channel", table_name="notifications")
    op.drop_index("ix_notifications_kind", table_name="notifications")
    op.drop_index("ix_notifications_request_id", table_name="notifications")
    op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
    op.drop_table("notifications")
