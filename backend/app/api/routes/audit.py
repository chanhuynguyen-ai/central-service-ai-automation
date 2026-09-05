from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.models import AuditEvent, User
from app.schemas.activity import AuditOut, AuditPage
from app.services.audit import record_audit, safe_details

router = APIRouter()


@router.get("/events", response_model=AuditPage)
def events(
    event_type: str | None = Query(default=None, max_length=60, pattern="^[a-z_]+$"),
    request_id: int | None = Query(default=None, ge=1),
    before_id: int | None = Query(default=None, ge=1), limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db), actor: User = Depends(require_roles("ADMIN", "AUDITOR")),
):
    query = db.query(AuditEvent)
    if event_type is not None:
        query = query.filter_by(event_type=event_type)
    if request_id is not None:
        query = query.filter_by(request_id=request_id)
    if before_id is not None:
        query = query.filter(AuditEvent.id < before_id)
    rows = query.order_by(AuditEvent.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        user = db.get(User, row.actor_id) if row.actor_id else None
        items.append(AuditOut(id=row.id, actor_id=row.actor_id, actor_name=user.full_name if user else None,
                    request_id=row.request_id, event_type=row.event_type, resource_type=row.resource_type,
                    resource_id=row.resource_id, correlation_id=row.correlation_id,
                    details=safe_details(row.details), created_at=row.created_at))
    # Record access AFTER selecting the page; no domain event and no form/body copy.
    record_audit(db, "audit_log_viewed", actor_id=actor.id, resource_type="audit_log")
    db.commit()
    return AuditPage(items=items, next_before_id=rows[-1].id if more else None)
