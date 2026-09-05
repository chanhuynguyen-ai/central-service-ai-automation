"""Destructive M5 concurrency probe for a disposable PostgreSQL database only."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

from sqlalchemy import text

from app.db.seed import seed_data
from app.db.seed_catalog import seed_catalog
from app.db.seed_workflows import seed_workflows
from app.db.session import SessionLocal
from app.models.catalog import RequestType, RequestTypeVersion
from app.models.fulfillment import ServiceWorkItem
from app.models.models import AuditEvent, ServiceRequest, User
from app.models.workflows import ApprovalTask, WorkflowInstance, WorkflowStepInstance
from app.schemas.drafts import DraftCreate
from app.schemas.fulfillment import WorkItemAction
from app.schemas.workflows import DecisionInput, SubmitInput
from app.services.drafts import create_draft
from app.services.fulfillment import FulfillmentError, act, ensure_work_item
from app.services.workflows import decide_task, submit_draft


def _claim(item_id: int, actor_id: int, barrier: Barrier) -> int:
    with SessionLocal() as db:
        db.execute(text("SET LOCAL lock_timeout = '10s'"))
        actor = db.get(User, actor_id)
        barrier.wait(timeout=10)
        try:
            act(db, actor, item_id, WorkItemAction(action="assign", version=1))
            db.commit()
            return 200
        except FulfillmentError as exc:
            db.rollback()
            return exc.status_code


def verify() -> None:
    if os.getenv("CENTRALOPS_E2E") != "1":
        raise RuntimeError("Requires explicit opt-in on a disposable CI/demo database.")

    with SessionLocal() as db:
        if db.get_bind().dialect.name != "postgresql":
            raise RuntimeError("Requires PostgreSQL, not SQLite.")
        seed_data(db)
        seed_catalog(db)
        seed_workflows(db)
        requester = db.query(User).filter_by(email="employee@centralops.demo").one()
        manager = db.query(User).filter_by(email="manager.finance@centralops.demo").one()
        lead = db.query(User).filter_by(email="service.lead@centralops.demo").one()
        agent = db.query(User).filter_by(email="service.agent@centralops.demo").one()
        version = db.query(RequestTypeVersion).join(RequestType).filter(
            RequestType.code == "IT_LAPTOP_REPLACEMENT",
            RequestTypeVersion.status == "PUBLISHED",
        ).one()
        draft = create_draft(
            db,
            requester,
            DraftCreate(
                request_type_version_id=version.id,
                title=f"Fulfillment race {uuid4().hex[:8]}",
                description="Disposable approved request used to verify M5 locking.",
                form_data={
                    "reason": "Hardware failure",
                    "device": "windows",
                    "cost_center": "TEST-001",
                },
            ),
        )
        submit_draft(db, requester, draft.id, SubmitInput(revision=draft.draft_revision))
        instance = db.query(WorkflowInstance).filter_by(request_id=draft.id).one()
        first = db.query(WorkflowStepInstance).filter_by(
            workflow_instance_id=instance.id,
            step_order=1,
        ).one()
        first_task = db.query(ApprovalTask).filter_by(workflow_step_instance_id=first.id).one()
        decide_task(
            db,
            manager,
            first_task.id,
            DecisionInput(version=first_task.version, decision="approve"),
        )
        second = db.query(WorkflowStepInstance).filter_by(
            workflow_instance_id=instance.id,
            step_order=2,
        ).one()
        second_task = db.query(ApprovalTask).filter_by(workflow_step_instance_id=second.id).one()
        request = decide_task(
            db,
            lead,
            second_task.id,
            DecisionInput(version=second_task.version, decision="approve"),
        )
        item = ensure_work_item(db, request, instance.snapshot, lead)
        request_id = request.id
        item_id = item.id
        agent_id = agent.id
        lead_id = lead.id
        db.commit()

    barrier = Barrier(2)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(_claim, item_id, agent_id, barrier),
            executor.submit(_claim, item_id, lead_id, barrier),
        ]
        statuses = sorted(future.result(timeout=25) for future in futures)
    assert statuses == [200, 409], statuses

    with SessionLocal() as db:
        item = db.get(ServiceWorkItem, item_id)
        request = db.get(ServiceRequest, request_id)
        assert item.status == "ASSIGNED"
        assert item.version == 2
        assert item.assignee_user_id in {agent_id, lead_id}
        assert request.fulfillment_state == "assigned"
        assert db.query(ServiceWorkItem).filter_by(request_id=request_id).count() == 1
        assert db.query(AuditEvent).filter_by(
            request_id=request_id,
            event_type="service_queued",
        ).count() == 1
        assert db.query(AuditEvent).filter_by(
            request_id=request_id,
            event_type="service_assigned",
        ).count() == 1

    print(
        "PASS: final approval created one work item; two concurrent claims produced "
        "one assignment and one 409 with one assignment audit event."
    )


if __name__ == "__main__":
    verify()
