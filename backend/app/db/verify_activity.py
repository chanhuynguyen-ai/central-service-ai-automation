"""Explicit opt-in M4 PostgreSQL verification on a disposable test database."""
import os
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.seed import seed_data
from app.db.seed_catalog import seed_catalog
from app.db.seed_workflows import seed_workflows
from app.db.session import SessionLocal
from app.db.verify_workflow_concurrency import race
from app.models.activity import RequestComment, RequestEvent
from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AuditEvent, User
from app.schemas.activity import CommentCreate
from app.schemas.drafts import DraftCreate
from app.schemas.workflows import SubmitInput
from app.services.activity import add_comment
from app.services.drafts import create_draft
from app.services.workflows import submit_draft


def verify():
    if os.getenv("CENTRALOPS_E2E") != "1":
        raise RuntimeError("Requires explicit opt-in on a disposable test database.")
    with SessionLocal() as db:
        bind = db.get_bind()
        if bind.dialect.name != "postgresql" or not (bind.url.database or "").endswith("_test"):
            raise RuntimeError("Requires PostgreSQL and a dedicated database ending in _test.")
        seed_data(db)
        seed_catalog(db)
        seed_workflows(db)
        actor = db.query(User).filter_by(email="employee@centralops.demo").one()
        version = db.query(RequestTypeVersion).join(RequestType).filter(
            RequestType.code == "IT_LAPTOP_REPLACEMENT", RequestTypeVersion.status == "PUBLISHED",
        ).one()
        draft = create_draft(db, actor, DraftCreate(request_type_version_id=version.id,
            title=f"M4 concurrency {uuid4().hex[:8]}", description="Verify private and public request activity.",
            form_data={"reason": "Test", "device": "windows", "cost_center": "TEST-ONLY"}))
        submit_draft(db, actor, draft.id, SubmitInput(revision=draft.draft_revision))
        request_id, actor_id = draft.id, actor.id
        db.commit()
    payload = CommentCreate(body="Concurrent idempotent public message", client_token=uuid4())
    assert race([actor_id, actor_id], lambda db, actor: add_comment(db, actor, request_id, payload)) == [200, 200]
    with SessionLocal() as db:
        comment = db.query(RequestComment).filter_by(request_id=request_id).one()
        audit = db.query(AuditEvent).filter_by(request_id=request_id, event_type="request_comment_added").one()
        domain = db.query(RequestEvent).filter_by(source_audit_id=audit.id).one()
        assert domain.payload == {"comment_id": comment.id}
        assert "message" not in str(audit.details)
        identities = {"request_comments": comment.id, "audit_events": audit.id, "request_events": domain.id}
        # Savepoints permit asserting all triggers without rolling back setup.
        for table, identity in identities.items():
            for statement in (f"UPDATE {table} SET id=id WHERE id=:id", f"DELETE FROM {table} WHERE id=:id", f"TRUNCATE TABLE {table} CASCADE"):
                try:
                    with db.begin_nested():
                        db.execute(text(statement), {"id": identity})
                except DBAPIError as exc:
                    assert "append-only" in str(exc), str(exc)
                else:
                    raise AssertionError(f"History mutation was not blocked: {table}")
        assert db.query(RequestComment).filter_by(request_id=request_id).count() == 1
        assert db.query(AuditEvent).filter_by(request_id=request_id, event_type="request_comment_added").count() == 1
        db.rollback()
    print("PASS: PostgreSQL concurrent comment retries -> one comment/audit/event; UPDATE, DELETE and TRUNCATE blocked")


if __name__ == "__main__":
    verify()
