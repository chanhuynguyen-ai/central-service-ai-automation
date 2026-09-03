from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import AuditEvent, ServiceRequest, User
from app.schemas.schemas import RequestCreate
from app.services.llm import TriageResult

SLA_HOURS = {"low": 72, "medium": 24, "high": 8, "urgent": 2}


def add_audit_event(
    db: Session,
    event_type: str,
    request: ServiceRequest | None = None,
    actor: User | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            request_id=request.id if request else None,
            actor_id=actor.id if actor else None,
            event_type=event_type,
            details=details or {},
        )
    )


def create_request(
    db: Session,
    payload: RequestCreate,
    requester: User,
    triage: TriageResult,
) -> ServiceRequest:
    priority = payload.priority or triage.priority
    category = payload.category or triage.category
    now = datetime.now(UTC)
    request = ServiceRequest(
        reference=f"PENDING-{int(now.timestamp() * 1000)}",
        title=payload.title,
        description=payload.description,
        category=category,
        priority=priority,
        department=requester.department,
        requester_id=requester.id,
        assigned_to="Central Service Approver",
        ai_summary=triage.summary,
        ai_category=triage.category,
        ai_priority=triage.priority,
        ai_confidence=triage.confidence,
        ai_model=triage.model,
        due_at=now + timedelta(hours=SLA_HOURS.get(priority, 24)),
    )
    db.add(request)
    db.flush()
    request.reference = f"CSR-{1000 + request.id}"
    add_audit_event(
        db,
        "request_created",
        request=request,
        actor=requester,
        details={"source": "web", "status": request.status},
    )
    add_audit_event(
        db,
        "ai_triage_completed",
        request=request,
        details={
            "category": triage.category,
            "priority": triage.priority,
            "confidence": triage.confidence,
            "provider": triage.provider,
            "latency_ms": triage.latency_ms,
        },
    )
    return request
