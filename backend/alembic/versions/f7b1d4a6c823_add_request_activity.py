"""Append-only request activity, comments and safe audit envelopes.

Revision ID: f7b1d4a6c823
Revises: e6a0c3f5b712
"""
import sqlalchemy as sa
from alembic import op

revision = "f7b1d4a6c823"
down_revision = "e6a0c3f5b712"
branch_labels = None
depends_on = None

TABLES = ("request_events", "request_comments", "audit_events")


def _backfill(bind):
    # Migration-local mapping: future application changes must not rewrite history.
    mapping = {"request_submitted": "REQUEST_SUBMITTED", "workflow_started": "WORKFLOW_STARTED",
               "approval_step_activated": "APPROVAL_ASSIGNED", "workflow_approved": "WORKFLOW_APPROVED"}
    integer_keys = {"instance_id", "attempt", "revision", "workflow_version_id", "step_id", "task_id"}
    audits = sa.table("audit_events", sa.column("id", sa.Integer), sa.column("request_id", sa.Integer),
                      sa.column("actor_id", sa.Integer), sa.column("event_type", sa.String),
                      sa.column("details", sa.JSON), sa.column("created_at", sa.DateTime(timezone=True)))
    requests = sa.table("service_requests", sa.column("id", sa.Integer),
                        sa.column("request_type_version_id", sa.Integer), sa.column("workflow_attempt", sa.Integer))
    events = sa.table("request_events", sa.column("request_id", sa.Integer), sa.column("actor_id", sa.Integer),
                      sa.column("event_type", sa.String), sa.column("visibility", sa.String), sa.column("payload", sa.JSON),
                      sa.column("source_audit_id", sa.Integer), sa.column("created_at", sa.DateTime(timezone=True)))
    cursor = 0
    while True:
        rows = bind.execute(sa.select(audits).join(requests, requests.c.id == audits.c.request_id).where(
            audits.c.id > cursor, requests.c.request_type_version_id.is_not(None), requests.c.workflow_attempt > 0,
            audits.c.event_type.in_([*mapping, "approval_decided"]),
        ).order_by(audits.c.id).limit(500)).mappings().all()
        if not rows:
            break
        for row in rows:
            details = row["details"] if isinstance(row["details"], dict) else {}
            decision = details.get("decision")
            kind = mapping.get(row["event_type"])
            if row["event_type"] == "approval_decided" and isinstance(decision, str):
                kind = {"approve": "APPROVAL_APPROVED", "reject": "APPROVAL_REJECTED",
                        "request_changes": "CHANGES_REQUESTED"}.get(decision)
            if not kind:
                continue
            payload = {key: value for key, value in details.items() if key in integer_keys and type(value) is int}
            payload["backfilled"] = True
            if isinstance(decision, str) and decision in {"approve", "reject", "request_changes"}:
                payload["decision"] = decision
            bind.execute(events.insert().values(request_id=row["request_id"], actor_id=row["actor_id"],
                event_type=kind, visibility="REQUESTER_VISIBLE", payload=payload,
                source_audit_id=row["id"], created_at=row["created_at"]))
        cursor = rows[-1]["id"]


def _protect(bind):
    if bind.dialect.name == "postgresql":
        op.execute("""CREATE FUNCTION centralops_reject_history_mutation() RETURNS trigger
        LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'History is append-only'; END; $$""")
        for table in TABLES:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION centralops_reject_history_mutation()")
            op.execute(f"CREATE TRIGGER {table}_no_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION centralops_reject_history_mutation()")
    elif bind.dialect.name == "sqlite":
        for table in TABLES:
            for action in ("UPDATE", "DELETE"):
                op.execute(f"CREATE TRIGGER {table}_no_{action.lower()} BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT, 'History is append-only'); END")


def upgrade():
    bind = op.get_bind()
    op.add_column("audit_events", sa.Column("resource_type", sa.String(40), nullable=True))
    op.add_column("audit_events", sa.Column("resource_id", sa.String(40), nullable=True))
    op.add_column("audit_events", sa.Column("correlation_id", sa.String(36), nullable=True))
    op.create_index("ix_audit_events_resource_type", "audit_events", ["resource_type"])
    op.create_table("request_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("service_requests.id"), nullable=False),
        sa.Column("actor_id", sa.Integer, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("visibility", sa.String(30), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False),
        sa.Column("source_audit_id", sa.Integer, sa.ForeignKey("audit_events.id"), unique=True, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("visibility IN ('REQUESTER_VISIBLE', 'INTERNAL')", name="ck_event_visibility"),
    )
    op.create_index("ix_request_events_request_id_id", "request_events", ["request_id", "id"])
    op.create_table("request_comments",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("request_id", sa.Integer, sa.ForeignKey("service_requests.id"), nullable=False),
        sa.Column("author_user_id", sa.Integer, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("visibility", sa.String(30), nullable=False),
        sa.Column("client_token", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("visibility IN ('REQUESTER_VISIBLE', 'INTERNAL')", name="ck_comment_visibility"),
        sa.UniqueConstraint("request_id", "author_user_id", "client_token", name="uq_comment_idempotency"),
    )
    op.create_index("ix_request_comments_request_id_id", "request_comments", ["request_id", "id"])
    _backfill(bind)
    _protect(bind)


def downgrade():
    bind = op.get_bind()
    for table in ("request_events", "request_comments"):
        if bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar():
            raise RuntimeError("Refusing to discard request history. Export and plan a data migration first.")
    if bind.execute(sa.text("SELECT COUNT(*) FROM audit_events WHERE resource_type IS NOT NULL")).scalar():
        raise RuntimeError("Refusing to discard enriched audit history.")
    if bind.dialect.name == "postgresql":
        for table in TABLES:
            op.execute(f"DROP TRIGGER {table}_immutable ON {table}")
            op.execute(f"DROP TRIGGER {table}_no_truncate ON {table}")
        op.execute("DROP FUNCTION centralops_reject_history_mutation()")
    elif bind.dialect.name == "sqlite":
        for table in TABLES:
            for action in ("update", "delete"):
                op.execute(f"DROP TRIGGER {table}_no_{action}")
    op.drop_table("request_comments")
    op.drop_table("request_events")
    op.drop_index("ix_audit_events_resource_type", table_name="audit_events")
    for column in ("correlation_id", "resource_id", "resource_type"):
        op.drop_column("audit_events", column)
