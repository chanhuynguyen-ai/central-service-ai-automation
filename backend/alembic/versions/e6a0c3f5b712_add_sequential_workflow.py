"""Sequential workflow definitions, immutable attempts and assigned decisions.

Revision ID: e6a0c3f5b712
Revises: d5f9b2e4a601
"""
from alembic import op
import sqlalchemy as sa

revision = "e6a0c3f5b712"
down_revision = "d5f9b2e4a601"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("service_requests", sa.Column("approval_state", sa.String(24), nullable=True))
    op.add_column("service_requests", sa.Column("fulfillment_state", sa.String(24), nullable=True))
    op.add_column("service_requests", sa.Column("workflow_attempt", sa.Integer(), server_default="0", nullable=False))
    op.add_column("service_requests", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table("workflow_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("request_type_id", sa.Integer(), sa.ForeignKey("request_types.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("workflow_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_definition_id", sa.Integer(), sa.ForeignKey("workflow_definitions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("approval_due_hours", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_definition_id", "version", name="uq_workflow_version"))
    op.create_index("ix_workflow_versions_workflow_definition_id", "workflow_versions", ["workflow_definition_id"])
    op.create_index("uq_workflow_published", "workflow_versions", ["workflow_definition_id"], unique=True,
                    postgresql_where=sa.text("status = 'PUBLISHED'"), sqlite_where=sa.text("status = 'PUBLISHED'"))
    op.create_table("workflow_step_definitions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_version_id", sa.Integer(), sa.ForeignKey("workflow_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False), sa.Column("name", sa.String(180), nullable=False),
        sa.Column("approval_mode", sa.String(10), nullable=False),
        sa.Column("approver_resolver_type", sa.String(20), nullable=False),
        sa.Column("approver_resolver_config", sa.JSON(), nullable=False),
        sa.UniqueConstraint("workflow_version_id", "step_order", name="uq_workflow_step_order"))
    op.create_index("ix_workflow_step_definitions_workflow_version_id", "workflow_step_definitions", ["workflow_version_id"])
    op.create_table("workflow_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.Integer(), sa.ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("workflow_version_id", sa.Integer(), sa.ForeignKey("workflow_versions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False), sa.Column("status", sa.String(24), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("request_id", "attempt", name="uq_workflow_attempt"))
    op.create_index("ix_workflow_instances_request_id", "workflow_instances", ["request_id"])
    op.create_index("uq_workflow_active_request", "workflow_instances", ["request_id"], unique=True,
                    postgresql_where=sa.text("status = 'PENDING'"), sqlite_where=sa.text("status = 'PENDING'"))
    op.create_table("workflow_step_instances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_instance_id", sa.Integer(), sa.ForeignKey("workflow_instances.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("step_order", sa.Integer(), nullable=False), sa.Column("name", sa.String(180), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("approver_ids", sa.JSON(), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_instance_id", "step_order", name="uq_workflow_runtime_step"))
    op.create_index("ix_workflow_step_instances_workflow_instance_id", "workflow_step_instances", ["workflow_instance_id"])
    op.create_table("approval_tasks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_step_instance_id", sa.Integer(), sa.ForeignKey("workflow_step_instances.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approver_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workflow_step_instance_id", "approver_user_id", name="uq_approval_task_assignee"))
    for column in ["workflow_step_instance_id", "approver_user_id", "status"]:
        op.create_index(f"ix_approval_tasks_{column}", "approval_tasks", [column])
    op.create_table("approval_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("approval_task_id", sa.Integer(), sa.ForeignKey("approval_tasks.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("decision", sa.String(24), nullable=False), sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT count(*) FROM workflow_definitions")).scalar():
        raise RuntimeError("Workflow data exists. Export/migrate it before downgrading; no history was deleted.")
    for table in ["approval_decisions", "approval_tasks", "workflow_step_instances", "workflow_instances", "workflow_step_definitions", "workflow_versions", "workflow_definitions"]:
        op.drop_table(table)
    with op.batch_alter_table("service_requests") as batch:
        for column in ["approved_at", "workflow_attempt", "fulfillment_state", "approval_state"]:
            batch.drop_column(column)
