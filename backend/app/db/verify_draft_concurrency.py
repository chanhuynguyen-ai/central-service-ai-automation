"""Destructive-to-demo-data smoke test for an isolated PostgreSQL CI stack only.

Requires CENTRALOPS_E2E=1. Leaves one test draft for inspection; never use on a
production database. Runs the real SQL compare-and-swap using two connections.
"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import text

from app.db.session import SessionLocal
from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AuditEvent, ServiceRequest, User
from app.schemas.drafts import DraftCreate, DraftUpdate
from app.services.drafts import DraftError, create_draft, update_draft


def verify() -> None:
    if os.getenv("CENTRALOPS_E2E") != "1":
        raise RuntimeError("Run only in an explicitly opted-in disposable CI stack.")
    with SessionLocal() as db:
        if db.get_bind().dialect.name != "postgresql":
            raise RuntimeError("This check requires real PostgreSQL, not SQLite.")
        actor = db.query(User).filter_by(email="employee@centralops.demo").one()
        version = db.query(RequestTypeVersion).join(RequestType).filter(
            RequestType.code == "IT_LAPTOP_REPLACEMENT",
            RequestTypeVersion.status == "PUBLISHED",
        ).one()
        draft = create_draft(db, actor, DraftCreate(request_type_version_id=version.id))
        draft_id, actor_id = draft.id, actor.id
        db.commit()
    barrier = Barrier(2)

    def writer(title: str) -> int:
        with SessionLocal() as db:
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            actor = db.get(User, actor_id)
            barrier.wait(timeout=10)
            try:
                update_draft(db, actor, draft_id, DraftUpdate(revision=1, title=title))
                db.commit()
                return 200
            except DraftError as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(writer, title) for title in ("Concurrent writer A", "Concurrent writer B")]
        statuses = sorted(future.result(timeout=20) for future in futures)
    assert statuses == [200, 409], statuses
    with SessionLocal() as db:
        saved = db.get(ServiceRequest, draft_id)
        assert saved.draft_revision == 2
        assert db.query(AuditEvent).filter_by(request_id=draft_id, event_type="draft_updated").count() == 1
        assert saved.submitted_at is None and saved.due_at is None
    print("PASS: real PostgreSQL concurrent draft saves -> one success, one 409, one audit event")


if __name__ == "__main__":
    verify()
