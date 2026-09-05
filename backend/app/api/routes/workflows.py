from collections.abc import Generator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import ServiceRequest, User
from app.models.workflows import (
    ApprovalTask,
    WorkflowDefinition,
    WorkflowInstance,
    WorkflowStepInstance,
    WorkflowVersion,
)
from app.schemas.workflows import (
    DecisionInput,
    SubmitInput,
    WorkflowActivationInput,
    WorkflowCreate,
    WorkflowDefinitionOut,
    WorkflowVersionInput,
)
from app.services import fulfillment as fulfillment_service
from app.services import workflows as service

router = APIRouter()


@contextmanager
def transaction(db: Session) -> Generator[None, None, None]:
    try:
        yield
        db.commit()
    except (service.WorkflowError, fulfillment_service.FulfillmentError) as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Conflicting workflow operation; reload and retry.") from exc


@router.get("/definitions", response_model=list[WorkflowDefinitionOut])
def definitions(db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN"))):
    return db.query(WorkflowDefinition).order_by(WorkflowDefinition.id).limit(500).all()


@router.post("/definitions", response_model=WorkflowDefinitionOut, status_code=201)
def create_definition(payload: WorkflowCreate, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN"))):
    with transaction(db):
        return WorkflowDefinitionOut.model_validate(service.create_definition(db, actor, payload))


@router.patch("/definitions/{definition_id}", response_model=WorkflowDefinitionOut)
def activate_definition(definition_id: int, payload: WorkflowActivationInput, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN"))):
    with transaction(db):
        definition = service._definition(db, definition_id)
        definition.is_active = payload.is_active
        service._audit(db, actor, "workflow_activation_changed", definition_id=definition.id, active=payload.is_active)
        return WorkflowDefinitionOut.model_validate(definition)


@router.get("/definitions/{definition_id}/versions")
def versions(definition_id: int, db: Session = Depends(get_db), _: User = Depends(require_roles("ADMIN"))):
    if db.get(WorkflowDefinition, definition_id) is None:
        raise HTTPException(404, "Workflow definition not found")
    return [service.version_output(db, row) for row in db.query(WorkflowVersion).filter_by(workflow_definition_id=definition_id).order_by(WorkflowVersion.version).all()]


@router.post("/definitions/{definition_id}/versions", status_code=201)
def create_version(definition_id: int, payload: WorkflowVersionInput, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN"))):
    with transaction(db):
        return service.version_output(db, service.create_version(db, actor, definition_id, payload))


@router.put("/definitions/{definition_id}/versions/{number}")
def edit_version(definition_id: int, number: int, payload: WorkflowVersionInput, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN"))):
    with transaction(db):
        return service.version_output(db, service.edit_version(db, actor, definition_id, number, payload))


@router.post("/definitions/{definition_id}/versions/{number}/publish")
def publish_version(definition_id: int, number: int, db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN"))):
    with transaction(db):
        return service.version_output(db, service.publish_version(db, actor, definition_id, number))


@router.get("/requests")
def list_submissions(
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    query = db.query(ServiceRequest).filter(ServiceRequest.workflow_attempt > 0, service.visibility_clause(actor))
    total = query.count()
    rows = query.order_by(ServiceRequest.updated_at.desc(), ServiceRequest.id.desc()).offset(offset).limit(limit).all()
    return {"items": [service.request_summary(db, row) for row in rows], "total": total}


@router.get("/requests/{request_id}")
def read_submission(request_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    try:
        return service.request_output(db, service.visible_request(db, actor, request_id), actor)
    except service.WorkflowError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/requests/{request_id}/submit")
def submit(request_id: int, payload: SubmitInput, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    with transaction(db):
        return service.request_output(db, service.submit_draft(db, actor, request_id, payload), actor)


@router.get("/approval-tasks")
def inbox(
    task_status: str = Query(default="pending", pattern="^(pending|history)$", alias="status"),
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    query = db.query(ApprovalTask, WorkflowStepInstance, WorkflowInstance, ServiceRequest).join(
        WorkflowStepInstance, ApprovalTask.workflow_step_instance_id == WorkflowStepInstance.id,
    ).join(WorkflowInstance, WorkflowStepInstance.workflow_instance_id == WorkflowInstance.id).join(
        ServiceRequest, WorkflowInstance.request_id == ServiceRequest.id,
    ).filter(ApprovalTask.approver_user_id == actor.id)
    query = query.filter(ApprovalTask.status == "PENDING") if task_status == "pending" else query.filter(ApprovalTask.status != "PENDING")
    total = query.count()
    rows = query.order_by(ApprovalTask.assigned_at.desc(), ApprovalTask.id.desc()).offset(offset).limit(limit).all()
    return {"items": [{"id": task.id, "version": task.version, "status": task.status,
                       "step_name": step.name, "request_id": request.id, "reference": request.reference,
                       "title": instance.snapshot["title"], "attempt": instance.attempt,
                       "requester_name": instance.snapshot["requester_name"]}
                      for task, step, instance, request in rows], "total": total}


@router.post("/approval-tasks/{task_id}/decisions")
def decide(task_id: int, payload: DecisionInput, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    with transaction(db):
        request = service.decide_task(db, actor, task_id, payload)
        if request.status == "approved" and request.fulfillment_state in {None, "not_started", "not_queued"}:
            instance = db.query(WorkflowInstance).filter_by(
                request_id=request.id, attempt=request.workflow_attempt,
            ).first()
            if instance is None:
                raise service.WorkflowError(409, "Approved workflow instance is unavailable")
            fulfillment_service.ensure_work_item(db, request, instance.snapshot, actor)
        return service.request_output(db, request, actor)
