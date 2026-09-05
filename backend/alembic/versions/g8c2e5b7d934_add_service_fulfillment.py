"""Add service fulfillment work items.

Revision ID: g8c2e5b7d934
Revises: f7b1d4a6c823
"""
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision = "g8c2e5b7d934"
down_revision = "f7b1d4a6c823"
branch_labels = None
depends_on = None


def _team_from_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return None
    direct = snapshot.get("owner_service_team_id")
    if type(direct) is int:
        return direct
    workflow = snapshot.get("workflow") if isinstance(snapshot.get("workflow"), dict) else {}
    for step in reversed(workflow.get("steps", [])):
        if isinstance(step, dict) and step.get("approver_resolver_type") == "TEAM_LEAD":
            config = step.get("approver_resolver_config")
            team_id = config.get("service_team_id") if isinstance(config, dict) else None
            if type(team_id) is int:
                return team_id
    return None


def upgrade():
    op.create_table(
        "service_work_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_team_id", sa.Integer(), sa.ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assignee_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("resolution_summary", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("waiting_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("request_id", name="uq_service_work_item_request"),
        sa.CheckConstraint("status IN ('QUEUED','ASSIGNED','IN_PROGRESS','WAITING_REQUESTER','RESOLVED','CLOSED')", name="ck_service_work_item_status"),
    )
    op.create_index("ix_service_work_items_request_id", "service_work_items", ["request_id"])
    op.create_index("ix_service_work_items_service_team_id", "service_work_items", ["service_team_id"])
    op.create_index("ix_service_work_items_assignee_user_id", "service_work_items", ["assignee_user_id"])
    op.create_index("ix_service_work_items_status", "service_work_items", ["status"])
    op.create_index("ix_service_work_items_team_status", "service_work_items", ["service_team_id", "status"])
    op.create_index("ix_service_work_items_assignee_status", "service_work_items", ["assignee_user_id", "status"])

    bind = op.get_bind()
    requests = sa.table("service_requests", sa.column("id", sa.Integer), sa.column("status", sa.String),
                        sa.column("approval_state", sa.String), sa.column("fulfillment_state", sa.String),
                        sa.column("approved_at", sa.DateTime(timezone=True)), sa.column("workflow_attempt", sa.Integer))
    instances = sa.table("workflow_instances", sa.column("request_id", sa.Integer), sa.column("attempt", sa.Integer),
                         sa.column("snapshot", sa.JSON))
    work = sa.table("service_work_items", sa.column("request_id", sa.Integer), sa.column("service_team_id", sa.Integer),
                    sa.column("status", sa.String), sa.column("version", sa.Integer),
                    sa.column("queued_at", sa.DateTime(timezone=True)), sa.column("created_at", sa.DateTime(timezone=True)),
                    sa.column("updated_at", sa.DateTime(timezone=True)))
    rows = bind.execute(sa.select(requests.c.id, requests.c.approved_at, instances.c.snapshot).join(
        instances, sa.and_(instances.c.request_id == requests.c.id, instances.c.attempt == requests.c.workflow_attempt)
    ).where(requests.c.status == "approved", requests.c.approval_state == "approved")).mappings().all()
    for row in rows:
        team_id = _team_from_snapshot(row["snapshot"])
        if team_id is None:
            continue
        stamp = row["approved_at"] or datetime.now(UTC)
        bind.execute(work.insert().values(request_id=row["id"], service_team_id=team_id, status="QUEUED",
                                          version=1, queued_at=stamp, created_at=stamp, updated_at=stamp))
        bind.execute(requests.update().where(requests.c.id == row["id"]).values(fulfillment_state="queued"))


def downgrade():
    bind = op.get_bind()
    count = bind.execute(sa.text("SELECT COUNT(*) FROM service_work_items WHERE status <> 'QUEUED' OR assignee_user_id IS NOT NULL")).scalar_one()
    if count:
        raise RuntimeError("Refusing downgrade: fulfillment work has progressed and would be lost")
    op.drop_index("ix_service_work_items_assignee_status", table_name="service_work_items")
    op.drop_index("ix_service_work_items_team_status", table_name="service_work_items")
    op.drop_index("ix_service_work_items_status", table_name="service_work_items")
    op.drop_index("ix_service_work_items_assignee_user_id", table_name="service_work_items")
    op.drop_index("ix_service_work_items_service_team_id", table_name="service_work_items")
    op.drop_index("ix_service_work_items_request_id", table_name="service_work_items")
    op.drop_table("service_work_items")
