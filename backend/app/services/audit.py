"""Safe audit envelopes and domain events; callers own the transaction.

Never copy request bodies, tokens, form values or comments into audit/timeline.
Unknown legacy metadata is omitted from the read API as well as from new writes.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import request_id_context
from app.models.activity import RequestEvent
from app.models.models import AuditEvent

INTEGER_KEYS = frozenset({
    "instance_id", "attempt", "revision", "workflow_version_id", "step_id", "task_id",
    "definition_id", "version_id", "request_type_id", "request_type_version_id",
    "comment_id", "user_id", "role_id", "session_id",
})
DOMAIN_EVENTS = {
    "request_submitted": "REQUEST_SUBMITTED", "workflow_started": "WORKFLOW_STARTED",
    "approval_step_activated": "APPROVAL_ASSIGNED", "workflow_approved": "WORKFLOW_APPROVED",
    "request_comment_added": "COMMENT_ADDED", "internal_note_added": "INTERNAL_NOTE_ADDED",
}


def safe_details(details: dict | None) -> dict:
    safe = {}
    for key, value in (details if isinstance(details, dict) else {}).items():
        if key in INTEGER_KEYS and isinstance(value, int) and not isinstance(value, bool):
            safe[key] = value
        elif key in {"active", "replayed", "backfilled"} and isinstance(value, bool):
            safe[key] = value
        elif key == "decision" and isinstance(value, str) and value in {"approve", "reject", "request_changes"}:
            safe[key] = value
    return safe


def domain_type(event_type: str, details: dict) -> str | None:
    if event_type == "approval_decided":
        return {"approve": "APPROVAL_APPROVED", "reject": "APPROVAL_REJECTED",
                "request_changes": "CHANGES_REQUESTED"}.get(details.get("decision"))
    return DOMAIN_EVENTS.get(event_type)


def record_audit(
    db: Session, event_type: str, *, actor_id: int | None = None,
    request_id: int | None = None, resource_type: str | None = None,
    resource_id: str | int | None = None, details: dict | None = None,
    domain: bool = False, internal: bool = False,
) -> AuditEvent:
    # X-Request-ID is client-controlled: only a UUID is allowed into the audit.
    try:
        correlation = str(UUID(request_id_context.get()))
    except (ValueError, TypeError, AttributeError):
        correlation = None
    safe = safe_details(details)
    row = AuditEvent(
        actor_id=actor_id, request_id=request_id, event_type=event_type,
        resource_type=resource_type or ("request" if request_id is not None else None),
        resource_id=str(resource_id if resource_id is not None else request_id) if resource_id is not None or request_id is not None else None,
        correlation_id=correlation, details=safe,
    )
    db.add(row)
    db.flush()
    kind = domain_type(event_type, safe) if domain else None
    if kind and request_id is not None:
        db.add(RequestEvent(
            request_id=request_id, actor_id=actor_id, event_type=kind,
            visibility="INTERNAL" if internal else "REQUESTER_VISIBLE",
            payload=safe, source_audit_id=row.id, created_at=row.created_at,
        ))
        db.flush()
    return row
