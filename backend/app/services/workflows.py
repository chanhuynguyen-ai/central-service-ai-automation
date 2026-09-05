"""Sequential ALL-approval runtime. Services never commit: routes own transactions.

Each submission freezes form values, workflow rules AND resolved participants.
Request row locks serialize decisions across all active tasks; SQL compare-and-
swap plus unique constraints protect stale clients and non-locking test stores.
"""
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select, update
from sqlalchemy.orm import Session

from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AuditEvent, Role, ServiceRequest, ServiceTeam, User, UserRole
from app.models.workflows import (
    ApprovalDecision,
    ApprovalTask,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStepDefinition,
    WorkflowStepInstance,
    WorkflowVersion,
)
from app.schemas.catalog import DynamicFormSchema
from app.schemas.workflows import DecisionInput, SubmitInput, WorkflowCreate, WorkflowVersionInput
from app.services.form_validation import validate_draft
from app.services.permissions import user_has_any_role


class WorkflowError(Exception):
    def __init__(self, code: int, detail: str | list[dict]) -> None:
        self.status_code = code
        self.detail = detail
        super().__init__(str(detail))


def _audit(db: Session, actor: User, event: str, request_id: int | None = None, **details) -> None:
    db.add(AuditEvent(actor_id=actor.id, request_id=request_id, event_type=event, details=details))


def _definition(db: Session, definition_id: int) -> WorkflowDefinition:
    definition = db.query(WorkflowDefinition).filter_by(id=definition_id).populate_existing().with_for_update().first()
    if definition is None:
        raise WorkflowError(404, "Workflow definition not found")
    return definition


def _version(db: Session, definition_id: int, number: int) -> WorkflowVersion:
    version = db.query(WorkflowVersion).filter_by(workflow_definition_id=definition_id, version=number).first()
    if version is None:
        raise WorkflowError(404, "Workflow version not found")
    return version


def definition_steps(db: Session, version_id: int) -> list[WorkflowStepDefinition]:
    return db.query(WorkflowStepDefinition).filter_by(workflow_version_id=version_id).order_by(WorkflowStepDefinition.step_order).all()


def version_output(db: Session, version: WorkflowVersion) -> dict:
    return {
        "id": version.id, "workflow_definition_id": version.workflow_definition_id,
        "version": version.version, "status": version.status,
        "approval_due_hours": version.approval_due_hours,
        "published_at": version.published_at.isoformat() if version.published_at else None,
        "steps": [{"name": step.name, "step_order": step.step_order,
                   "approval_mode": step.approval_mode,
                   "approver_resolver_type": step.approver_resolver_type,
                   "approver_resolver_config": step.approver_resolver_config}
                  for step in definition_steps(db, version.id)],
    }


def create_definition(db: Session, actor: User, payload: WorkflowCreate) -> WorkflowDefinition:
    if not db.get(RequestType, payload.request_type_id):
        raise WorkflowError(404, "Request type not found")
    definition = WorkflowDefinition(**payload.model_dump())
    db.add(definition)
    db.flush()  # Unique code and one default definition per request type.
    _audit(db, actor, "workflow_definition_created", definition_id=definition.id)
    return definition


def create_version(db: Session, actor: User, definition_id: int, payload: WorkflowVersionInput) -> WorkflowVersion:
    _definition(db, definition_id)
    number = (db.query(func.max(WorkflowVersion.version)).filter_by(workflow_definition_id=definition_id).scalar() or 0) + 1
    version = WorkflowVersion(workflow_definition_id=definition_id, version=number,
                              approval_due_hours=payload.approval_due_hours, created_by=actor.id)
    db.add(version)
    db.flush()
    _set_steps(db, version, payload)
    _audit(db, actor, "workflow_version_created", version_id=version.id)
    return version


def _set_steps(db: Session, version: WorkflowVersion, payload: WorkflowVersionInput) -> None:
    version.approval_due_hours = payload.approval_due_hours
    for order, spec in enumerate(payload.steps, start=1):
        db.add(WorkflowStepDefinition(workflow_version_id=version.id, step_order=order,
               name=spec.name, approval_mode=spec.approval_mode,
               approver_resolver_type=spec.approver_resolver_type,
               approver_resolver_config=spec.approver_resolver_config.model_dump(exclude_none=True)))
    db.flush()


def edit_version(db: Session, actor: User, definition_id: int, number: int, payload: WorkflowVersionInput) -> WorkflowVersion:
    _definition(db, definition_id)
    version = _version(db, definition_id, number)
    if version.status != "DRAFT":
        raise WorkflowError(409, "Published and retired workflow versions are immutable")
    db.query(WorkflowStepDefinition).filter_by(workflow_version_id=version.id).delete(synchronize_session=False)
    _set_steps(db, version, payload)
    _audit(db, actor, "workflow_version_updated", version_id=version.id)
    return version


def publish_version(db: Session, actor: User, definition_id: int, number: int) -> WorkflowVersion:
    definition = _definition(db, definition_id)
    if not definition.is_active:
        raise WorkflowError(409, "Activate the workflow before publishing")
    version = _version(db, definition_id, number)
    if version.status == "PUBLISHED":
        return version
    if version.status != "DRAFT" or not definition_steps(db, version.id):
        raise WorkflowError(409, "Only nonempty draft versions can be published")
    db.query(WorkflowVersion).filter_by(workflow_definition_id=definition_id, status="PUBLISHED").update({"status": "RETIRED"}, synchronize_session=False)
    db.flush()
    version.status = "PUBLISHED"
    version.published_at = datetime.now(UTC)
    db.flush()
    _audit(db, actor, "workflow_version_published", version_id=version.id)
    return version


def _eligible(user: User | None) -> bool:
    return bool(user and user.is_active and user_has_any_role(user, "APPROVER", "ADMIN"))


def resolve_approvers(db: Session, step: WorkflowStepDefinition, requester: User, kind: RequestType) -> list[int]:
    config = step.approver_resolver_config
    resolver = step.approver_resolver_type
    if resolver == "USER":
        users = [db.get(User, config["user_id"])]
    elif resolver == "MANAGER":
        users = [db.get(User, requester.manager_id)] if requester.manager_id else []
    elif resolver == "ROLE":
        users = db.query(User).join(UserRole, UserRole.user_id == User.id).join(Role, Role.id == UserRole.role_id).filter(
            User.department_id == requester.department_id,
            User.is_active.is_(True), Role.code == config["role_code"],
        ).order_by(User.id).all() if requester.department_id else []
    elif resolver == "TEAM_LEAD":
        team_id = config.get("service_team_id") or kind.owner_service_team_id
        team = db.get(ServiceTeam, team_id) if team_id else None
        users = [db.get(User, team.lead_user_id)] if team and team.is_active and team.lead_user_id else []
    else:
        raise WorkflowError(409, "Unsupported approver resolver")
    if not users or len(users) > 50 or any(not _eligible(user) for user in users):
        raise WorkflowError(409, "Routing requires administrator attention: no valid active approver.")
    ids = sorted({user.id for user in users})
    if requester.id in ids:
        raise WorkflowError(409, "Routing would allow self approval; administrator action is required.")
    return ids


def _lock_request(db: Session, request_id: int) -> ServiceRequest:
    request = db.query(ServiceRequest).filter_by(id=request_id).populate_existing().with_for_update().first()
    if request is None or request.request_type_version_id is None:
        raise WorkflowError(404, "Structured request not found")
    return request


def submit_draft(db: Session, actor: User, request_id: int, payload: SubmitInput) -> ServiceRequest:
    request = _lock_request(db, request_id)
    if request.requester_id != actor.id:
        raise WorkflowError(404, "Draft not found")
    if request.status not in {"draft", "changes_requested"} or request.draft_revision != payload.revision:
        raise WorkflowError(409, "Request changed or was already submitted. Reload before submitting.")
    version = db.get(RequestTypeVersion, request.request_type_version_id)
    kind = db.get(RequestType, version.request_type_id) if version else None
    if not kind or not kind.is_active or version.status not in {"PUBLISHED", "RETIRED"}:
        raise WorkflowError(409, "The pinned catalog version is unavailable")
    schema = DynamicFormSchema.model_validate(version.form_schema)
    validation = validate_draft(request.title, request.description, schema, request.form_data,
                                db=db, validation_schema=version.validation_schema)
    if not validation.valid:
        raise WorkflowError(422, [issue.model_dump() for issue in validation.errors])
    # One default definition per type; no LLM or condition interpreter chooses it.
    definition = db.query(WorkflowDefinition).filter_by(request_type_id=kind.id).populate_existing().with_for_update().first()
    if definition is None or not definition.is_active:
        raise WorkflowError(409, "No active workflow is configured for this service.")
    workflow_version = db.query(WorkflowVersion).filter_by(workflow_definition_id=definition.id, status="PUBLISHED").first()
    if workflow_version is None:
        raise WorkflowError(409, "No published workflow is configured for this service.")
    specs = definition_steps(db, workflow_version.id)
    if not specs:
        raise WorkflowError(409, "The workflow has no approval steps")
    # Fail atomically before mutation if ANY step has an unresolved/self approver.
    resolved = [resolve_approvers(db, spec, actor, kind) for spec in specs]
    now = datetime.now(UTC)
    attempt = request.workflow_attempt + 1
    changed = db.execute(update(ServiceRequest).where(
        ServiceRequest.id == request.id, ServiceRequest.requester_id == actor.id,
        ServiceRequest.status.in_(["draft", "changes_requested"]),
        ServiceRequest.draft_revision == payload.revision,
    ).values(status="pending_approval", approval_state="pending", fulfillment_state="not_started",
             workflow_attempt=attempt, draft_revision=payload.revision + 1, submitted_at=now,
             due_at=now + timedelta(hours=workflow_version.approval_due_hours),
             approved_at=None, completed_at=None, updated_at=now).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise WorkflowError(409, "Request changed while submitting; reload it.")
    db.refresh(request)
    snapshot = {
        "title": request.title, "description": request.description,
        "form_data": deepcopy(request.form_data), "form_schema": deepcopy(version.form_schema),
        "request_type_version_id": version.id, "form_version": version.version,
        "request_type_code": kind.code, "owner_service_team_id": kind.owner_service_team_id,
        "requester_name": actor.full_name, "requester_department": actor.department,
        "workflow": version_output(db, workflow_version),
        "resolved_approvers": resolved,
    }
    instance = WorkflowInstance(request_id=request.id, workflow_version_id=workflow_version.id,
                                attempt=attempt, snapshot=snapshot, started_at=now)
    db.add(instance)
    db.flush()
    runtime_steps = []
    for spec, approvers in zip(specs, resolved, strict=True):
        step = WorkflowStepInstance(workflow_instance_id=instance.id, step_order=spec.step_order,
                                    name=spec.name, approver_ids=approvers)
        db.add(step)
        runtime_steps.append(step)
    db.flush()
    _activate(db, runtime_steps[0], actor, request.id)
    _audit(db, actor, "request_submitted", request.id, instance_id=instance.id, attempt=attempt, revision=request.draft_revision)
    _audit(db, actor, "workflow_started", request.id, instance_id=instance.id, workflow_version_id=workflow_version.id)
    return request


def _activate(db: Session, step: WorkflowStepInstance, actor: User, request_id: int) -> None:
    users = [db.get(User, user_id) for user_id in step.approver_ids]
    if not users or any(not _eligible(user) for user in users):
        raise WorkflowError(409, "A snapshotted approver is unavailable; contact the workflow administrator.")
    step.status = "ACTIVE"
    step.activated_at = datetime.now(UTC)
    for user_id in step.approver_ids:
        db.add(ApprovalTask(workflow_step_instance_id=step.id, approver_user_id=user_id))
    db.flush()
    _audit(db, actor, "approval_step_activated", request_id, step_id=step.id)


def decide_task(db: Session, actor: User, task_id: int, payload: DecisionInput) -> ServiceRequest:
    row = db.query(ApprovalTask, WorkflowStepInstance, WorkflowInstance).join(
        WorkflowStepInstance, ApprovalTask.workflow_step_instance_id == WorkflowStepInstance.id,
    ).join(WorkflowInstance, WorkflowStepInstance.workflow_instance_id == WorkflowInstance.id).filter(ApprovalTask.id == task_id).first()
    if row is None:
        raise WorkflowError(404, "Approval task not found")
    task, step, instance = row
    if task.approver_user_id != actor.id or not _eligible(actor):
        raise WorkflowError(403, "This approval task is not assigned to you")
    request = _lock_request(db, instance.request_id)
    # Refresh objects loaded before waiting for a concurrent request-row lock.
    db.refresh(task)
    db.refresh(step)
    db.refresh(instance)
    if request.requester_id == actor.id:
        raise WorkflowError(403, "Self approval is forbidden")
    if task.status != "PENDING" or task.version != payload.version or step.status != "ACTIVE" or instance.status != "PENDING" or request.status != "pending_approval" or request.workflow_attempt != instance.attempt:
        raise WorkflowError(409, "The approval task is no longer pending. Reload the inbox.")
    now = datetime.now(UTC)
    status = {"approve": "APPROVED", "reject": "REJECTED", "request_changes": "CHANGES_REQUESTED"}[payload.decision]
    changed = db.execute(update(ApprovalTask).where(
        ApprovalTask.id == task.id, ApprovalTask.version == payload.version,
        ApprovalTask.status == "PENDING", ApprovalTask.approver_user_id == actor.id,
    ).values(status=status, version=payload.version + 1, acted_at=now).execution_options(synchronize_session=False))
    if changed.rowcount != 1:
        raise WorkflowError(409, "This approval task was already decided")
    db.refresh(task)
    db.add(ApprovalDecision(approval_task_id=task.id, actor_user_id=actor.id,
                            decision=payload.decision, comment=payload.comment))
    db.flush()
    _audit(db, actor, "approval_decided", request.id, task_id=task.id, decision=payload.decision, attempt=instance.attempt)
    if payload.decision != "approve":
        step.status = status
        step.completed_at = now
        instance.status = status
        instance.completed_at = now
        step_ids = select(WorkflowStepInstance.id).where(WorkflowStepInstance.workflow_instance_id == instance.id)
        db.query(ApprovalTask).filter(ApprovalTask.workflow_step_instance_id.in_(step_ids), ApprovalTask.status == "PENDING").update({"status": "CANCELLED", "acted_at": now, "version": ApprovalTask.version + 1}, synchronize_session=False)
        db.query(WorkflowStepInstance).filter_by(workflow_instance_id=instance.id, status="PENDING").update({"status": "CANCELLED", "completed_at": now}, synchronize_session=False)
        request.status = "rejected" if payload.decision == "reject" else "changes_requested"
        request.approval_state = request.status
        request.due_at = None
        request.draft_revision += 1
    else:
        remaining = db.query(ApprovalTask).filter_by(workflow_step_instance_id=step.id, status="PENDING").count()
        if remaining == 0:
            step.status = "APPROVED"
            step.completed_at = now
            next_step = db.query(WorkflowStepInstance).filter_by(workflow_instance_id=instance.id, step_order=step.step_order + 1).first()
            if next_step:
                _activate(db, next_step, actor, request.id)
            else:
                instance.status = "APPROVED"
                instance.completed_at = now
                request.status = "approved"
                request.approval_state = "approved"
                # Approval is NOT fulfillment; service work items belong to Phase 7.
                request.fulfillment_state = "not_queued"
                request.approved_at = now
                _audit(db, actor, "workflow_approved", request.id, instance_id=instance.id)
    request.updated_at = now
    db.flush()
    return request


def visibility_clause(actor: User):
    assigned = exists(select(ApprovalTask.id).join(
        WorkflowStepInstance, ApprovalTask.workflow_step_instance_id == WorkflowStepInstance.id,
    ).join(WorkflowInstance, WorkflowStepInstance.workflow_instance_id == WorkflowInstance.id).where(
        WorkflowInstance.request_id == ServiceRequest.id, ApprovalTask.approver_user_id == actor.id,
    ))
    clauses = [ServiceRequest.requester_id == actor.id, assigned]
    if user_has_any_role(actor, "MANAGER"):
        clauses.append(ServiceRequest.requester_id.in_(select(User.id).where(User.manager_id == actor.id)))
    if user_has_any_role(actor, "ADMIN", "AUDITOR"):
        return ServiceRequest.request_type_version_id.is_not(None)
    return and_(ServiceRequest.request_type_version_id.is_not(None), or_(*clauses))


def visible_request(db: Session, actor: User, request_id: int) -> ServiceRequest:
    request = db.query(ServiceRequest).filter(
        ServiceRequest.id == request_id, ServiceRequest.status != "draft", visibility_clause(actor),
    ).first()
    if request is None:
        raise WorkflowError(404, "Submitted request not found")
    return request


def request_summary(db: Session, request: ServiceRequest) -> dict:
    instance = db.query(WorkflowInstance).filter_by(request_id=request.id, attempt=request.workflow_attempt).first()
    if instance is None:
        raise WorkflowError(404, "Submitted workflow not found")
    # Always display submitted values, not a private edit in CHANGES_REQUESTED.
    return {"id": request.id, "reference": request.reference, "title": instance.snapshot["title"],
            "status": request.status, "approval_state": request.approval_state,
            "fulfillment_state": request.fulfillment_state, "revision": request.draft_revision,
            "requester_id": request.requester_id, "requester_name": instance.snapshot["requester_name"],
            "requester_department": instance.snapshot["requester_department"],
            "attempt": instance.attempt, "submitted_at": request.submitted_at,
            "due_at": request.due_at, "approved_at": request.approved_at}


def request_output(db: Session, request: ServiceRequest, actor: User) -> dict:
    result = request_summary(db, request)
    attempts = []
    for instance in db.query(WorkflowInstance).filter_by(request_id=request.id).order_by(WorkflowInstance.attempt).all():
        steps = []
        for step in db.query(WorkflowStepInstance).populate_existing().filter_by(workflow_instance_id=instance.id).order_by(WorkflowStepInstance.step_order).all():
            tasks = []
            for task in db.query(ApprovalTask).populate_existing().filter_by(workflow_step_instance_id=step.id).order_by(ApprovalTask.id).all():
                decision = db.query(ApprovalDecision).filter_by(approval_task_id=task.id).first()
                user = db.get(User, task.approver_user_id)
                tasks.append({"id": task.id, "approver_user_id": task.approver_user_id,
                              "approver_name": user.full_name, "status": task.status, "version": task.version,
                              "can_decide": task.approver_user_id == actor.id and _eligible(actor) and actor.id != request.requester_id and task.status == "PENDING" and step.status == "ACTIVE" and instance.status == "PENDING",
                              "decision": {"decision": decision.decision, "comment": decision.comment,
                                           "created_at": decision.created_at} if decision else None})
            steps.append({"id": step.id, "name": step.name, "step_order": step.step_order,
                          "status": step.status, "tasks": tasks})
        attempts.append({"id": instance.id, "attempt": instance.attempt, "status": instance.status,
                         "started_at": instance.started_at, "completed_at": instance.completed_at,
                         "snapshot": instance.snapshot, "steps": steps})
    return {**result, "attempts": attempts}
