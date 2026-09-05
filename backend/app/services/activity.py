"""M4 access policies are checked before queries/pagination, never only in UI."""
from sqlalchemy.orm import Session

from app.models.activity import RequestComment, RequestEvent
from app.models.models import ServiceRequest, User
from app.models.workflows import ApprovalTask, WorkflowInstance, WorkflowStepInstance
from app.schemas.activity import ActivityPermissions, CommentCreate, CommentOut
from app.services.audit import record_audit
from app.services.permissions import user_has_any_role
from app.services.workflows import WorkflowError, visible_request


def permissions(db: Session, actor: User, request: ServiceRequest) -> ActivityPermissions:
    assigned = db.query(ApprovalTask.id).join(
        WorkflowStepInstance, ApprovalTask.workflow_step_instance_id == WorkflowStepInstance.id,
    ).join(WorkflowInstance, WorkflowStepInstance.workflow_instance_id == WorkflowInstance.id).filter(
        WorkflowInstance.request_id == request.id, ApprovalTask.approver_user_id == actor.id,
    ).first() is not None
    owner = request.requester_id == actor.id
    admin = user_has_any_role(actor, "ADMIN")
    auditor_only = user_has_any_role(actor, "AUDITOR") and not user_has_any_role(actor, "ADMIN", "APPROVER", "MANAGER")
    reviewer = assigned and user_has_any_role(actor, "APPROVER", "ADMIN")
    requester = db.get(User, request.requester_id)
    direct_manager = bool(requester and requester.manager_id == actor.id and user_has_any_role(actor, "MANAGER"))
    # Being the requester always excludes internal content, even with another role.
    read_internal = not owner and (admin or reviewer or user_has_any_role(actor, "AUDITOR"))
    return ActivityPermissions(
        # AUDITOR grants organization-wide reads, never a broader writing scope
        # merely by being combined with an unrelated manager/approver role.
        can_comment=not auditor_only and (owner or admin or reviewer or direct_manager),
        can_read_internal=read_internal,
        can_write_internal=not owner and (admin or reviewer) and not auditor_only,
    )


def scoped_request(db: Session, actor: User, request_id: int) -> ServiceRequest:
    request = visible_request(db, actor, request_id)
    if request.workflow_attempt < 1:
        raise WorkflowError(404, "Submitted request not found")
    return request


def comment_output(db: Session, comment: RequestComment) -> CommentOut:
    author = db.get(User, comment.author_user_id)
    return CommentOut(
        id=comment.id, request_id=comment.request_id, author_user_id=comment.author_user_id,
        author_name=author.full_name if author else "Former user", body=comment.body,
        visibility=comment.visibility, created_at=comment.created_at,
    )


def add_comment(db: Session, actor: User, request_id: int, payload: CommentCreate) -> tuple[RequestComment, bool]:
    request = scoped_request(db, actor, request_id)
    # Serialize retries of the same idempotency key, and align with M3 decisions.
    db.query(ServiceRequest).filter_by(id=request.id).populate_existing().with_for_update().one()
    access = permissions(db, actor, request)
    if not access.can_comment or (payload.visibility == "INTERNAL" and not access.can_write_internal):
        raise WorkflowError(403, "You cannot post this type of comment")
    existing = db.query(RequestComment).filter_by(
        request_id=request.id, author_user_id=actor.id, client_token=str(payload.client_token),
    ).first()
    if existing:
        if existing.body != payload.body or existing.visibility != payload.visibility:
            raise WorkflowError(409, "This comment key was already used for different content")
        return existing, False
    comment = RequestComment(request_id=request.id, author_user_id=actor.id, body=payload.body,
                             visibility=payload.visibility, client_token=str(payload.client_token))
    db.add(comment)
    db.flush()
    internal = payload.visibility == "INTERNAL"
    record_audit(db, "internal_note_added" if internal else "request_comment_added", actor_id=actor.id,
                 request_id=request.id, details={"comment_id": comment.id}, domain=True, internal=internal)
    return comment, True


def event_query(db: Session, actor: User, request: ServiceRequest):
    query = db.query(RequestEvent).filter_by(request_id=request.id)
    if not permissions(db, actor, request).can_read_internal:
        query = query.filter_by(visibility="REQUESTER_VISIBLE")
    return query
