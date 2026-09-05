"""Opt-in destructive-to-demo-data concurrency probes on disposable PostgreSQL.

Two independent connections contend for submission and decision transitions.
Never run against production; no credentials or form values are printed.
"""
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
from app.models.models import AuditEvent, ServiceRequest, User
from app.models.workflows import (
    ApprovalDecision,
    ApprovalTask,
    WorkflowInstance,
    WorkflowStepInstance,
)
from app.schemas.drafts import DraftCreate
from app.schemas.workflows import DecisionInput, SubmitInput
from app.services.drafts import create_draft
from app.services.workflows import WorkflowError, decide_task, submit_draft


def race(actor_ids: list[int], operation) -> list[int]:
    barrier = Barrier(2)

    def contender(actor_id: int) -> int:
        with SessionLocal() as db:
            db.execute(text("SET LOCAL lock_timeout = '10s'"))
            actor = db.get(User, actor_id)
            barrier.wait(timeout=10)
            try:
                operation(db, actor)
                db.commit()
                return 200
            except WorkflowError as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(contender, actor_id) for actor_id in actor_ids]
        return sorted(future.result(timeout=25) for future in futures)


def verify() -> None:
    if os.getenv("CENTRALOPS_E2E") != "1":
        raise RuntimeError("Requires explicit opt-in on a disposable CI/demo database.")
    with SessionLocal() as db:
        if db.get_bind().dialect.name != "postgresql":
            raise RuntimeError("Requires PostgreSQL, not SQLite.")
        seed_data(db)
        seed_catalog(db)
        seed_workflows(db)
        actor = db.query(User).filter_by(email="employee@centralops.demo").one()
        manager = db.query(User).filter_by(email="manager.finance@centralops.demo").one()
        lead = db.query(User).filter_by(email="service.lead@centralops.demo").one()
        version = db.query(RequestTypeVersion).join(RequestType).filter(
            RequestType.code == "IT_LAPTOP_REPLACEMENT", RequestTypeVersion.status == "PUBLISHED",
        ).one()
        draft = create_draft(db, actor, DraftCreate(
            request_type_version_id=version.id, title=f"Concurrency probe {uuid4().hex[:8]}",
            description="Disposable test of concurrent workflow submission and decision.",
            form_data={"reason": "Unstable hardware", "device": "windows", "cost_center": "TEST-001"},
        ))
        request_id, actor_id, manager_id, lead_id = draft.id, actor.id, manager.id, lead.id
        revision = draft.draft_revision
        db.commit()
    statuses = race([actor_id, actor_id], lambda db, actor: submit_draft(db, actor, request_id, SubmitInput(revision=revision)))
    assert statuses == [200, 409], statuses
    with SessionLocal() as db:
        assert db.query(WorkflowInstance).filter_by(request_id=request_id).count() == 1
        assert db.query(AuditEvent).filter_by(request_id=request_id, event_type="request_submitted").count() == 1
        instance = db.query(WorkflowInstance).filter_by(request_id=request_id).one()
        instance_id = instance.id
        first = db.query(WorkflowStepInstance).filter_by(workflow_instance_id=instance_id, step_order=1).one()
        task = db.query(ApprovalTask).filter_by(workflow_step_instance_id=first.id).one()
        first_id, first_version = task.id, task.version
    statuses = race([manager_id, manager_id], lambda db, actor: decide_task(db, actor, first_id, DecisionInput(version=first_version, decision="approve")))
    assert statuses == [200, 409], statuses
    with SessionLocal() as db:
        assert db.query(ApprovalDecision).filter_by(approval_task_id=first_id).count() == 1
        second = db.query(WorkflowStepInstance).filter_by(workflow_instance_id=instance_id, step_order=2).one()
        task = db.query(ApprovalTask).filter_by(workflow_step_instance_id=second.id).one()
        second_id, second_version = task.id, task.version
        assert db.get(ServiceRequest, request_id).status == "pending_approval"
    statuses = race([lead_id, lead_id], lambda db, actor: decide_task(db, actor, second_id, DecisionInput(version=second_version, decision="approve")))
    assert statuses == [200, 409], statuses
    with SessionLocal() as db:
        request = db.get(ServiceRequest, request_id)
        assert request.status == "approved" and request.fulfillment_state == "not_queued"
        assert db.query(ApprovalDecision).filter_by(approval_task_id=second_id).count() == 1
        assert db.query(AuditEvent).filter_by(request_id=request_id, event_type="workflow_approved").count() == 1
    verify_distinct_all_tasks()
    print("PASS: PostgreSQL concurrent submit/step decision/final decision each -> one success, one 409; no duplicate workflow, task or decision.")


def verify_distinct_all_tasks() -> None:
    # Race DIFFERENT task IDs: the shared aggregate lock must serialize them.
    from app.models.models import Role, UserRole
    from app.models.workflows import WorkflowDefinition, WorkflowStepDefinition, WorkflowVersion

    with SessionLocal() as db:
        requester = db.query(User).filter_by(email="employee@centralops.demo").one()
        manager = db.query(User).filter_by(email="manager.finance@centralops.demo").one()
        lead = db.query(User).filter_by(email="service.lead@centralops.demo").one()
        code = "CONCURRENCY_" + uuid4().hex[:12].upper()
        kind = RequestType(code=code, category="Test", is_active=True)
        db.add(kind)
        db.flush()
        form = RequestTypeVersion(request_type_id=kind.id, version=1, title="Concurrent ALL test", status="PUBLISHED", form_schema={"sections": [{"title": "Details", "fields": [{"key": "reason", "type": "text", "label": "Reason", "required": True}]}]})
        db.add(form)
        db.flush()
        definition = WorkflowDefinition(code=code, name="Concurrent ALL", request_type_id=kind.id)
        db.add(definition)
        db.flush()
        version = WorkflowVersion(workflow_definition_id=definition.id, version=1, status="PUBLISHED", created_by=lead.id)
        db.add(version)
        db.flush()
        # Dedicated role limits this probe to exactly two eligible assignees.
        role = Role(code=code, name="Concurrency probe role")
        db.add(role)
        db.flush()
        lead.department_id = requester.department_id
        db.add_all([UserRole(user_id=manager.id, role_id=role.id), UserRole(user_id=lead.id, role_id=role.id)])
        db.add(WorkflowStepDefinition(workflow_version_id=version.id, step_order=1, name="All reviewers", approval_mode="ALL", approver_resolver_type="ROLE", approver_resolver_config={"role_code": code}))
        db.flush()
        draft = create_draft(db, requester, DraftCreate(request_type_version_id=form.id, title="Concurrent different tasks", description="Both active assignees decide concurrently without lost completion.", form_data={"reason": "Concurrency testing"}))
        submit_draft(db, requester, draft.id, SubmitInput(revision=1))
        request_id = draft.id
        instance = db.query(WorkflowInstance).filter_by(request_id=request_id).one()
        step = db.query(WorkflowStepInstance).filter_by(workflow_instance_id=instance.id).one()
        tasks = db.query(ApprovalTask).filter_by(workflow_step_instance_id=step.id).all()
        task_by_user = {task.approver_user_id: task.id for task in tasks}
        assert len(task_by_user) == 2
        db.commit()
    statuses = race(list(task_by_user), lambda db, actor: decide_task(db, actor, task_by_user[actor.id], DecisionInput(version=1, decision="approve")))
    assert statuses == [200, 200], statuses
    with SessionLocal() as db:
        assert db.get(ServiceRequest, request_id).status == "approved"
        assert db.query(ApprovalDecision).filter(ApprovalDecision.approval_task_id.in_(list(task_by_user.values()))).count() == 2
        assert db.query(AuditEvent).filter_by(request_id=request_id, event_type="workflow_approved").count() == 1
    print("PASS: two different ALL-assignee tasks decide concurrently -> two decisions, one final workflow completion")


if __name__ == "__main__":
    verify()
