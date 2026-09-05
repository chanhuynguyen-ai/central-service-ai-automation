import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Approval, ServiceRequest, User
from app.schemas.schemas import (
    AnalyticsFeedRow,
    PowerPlatformDecision,
    PowerPlatformIntake,
    RequestCreate,
    RequestOut,
)
from app.services.llm import ai_service
from app.services.workflow import add_audit_event, create_request

router = APIRouter()


def as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def verify_integration_key(x_integration_key: str = Header()) -> None:
    if not secrets.compare_digest(x_integration_key, settings.integration_api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid integration key")


@router.post(
    "/intake", response_model=RequestOut, status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_integration_key)],
)
def intake_from_power_apps(payload: PowerPlatformIntake, db: Session = Depends(get_db)) -> ServiceRequest:
    requester = db.query(User).filter(User.email == payload.requester_email).first()
    if not requester:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Requester not found")
    request_payload = RequestCreate(
        title=payload.title, description=payload.description,
        category=payload.category, priority=payload.priority,
    )
    triage = ai_service.triage(db, payload.title, payload.description)
    request = create_request(db, request_payload, requester, triage)
    if payload.source_record_id:
        request.reference = f"PA-{payload.source_record_id[:20]}-{request.id}"
    db.commit()
    db.refresh(request)
    return request


@router.get(
    "/requests/{reference}", response_model=RequestOut,
    dependencies=[Depends(verify_integration_key)],
)
def request_status(reference: str, db: Session = Depends(get_db)) -> ServiceRequest:
    request = (
        db.query(ServiceRequest).filter(ServiceRequest.status != "draft")
        .options(joinedload(ServiceRequest.requester))
        .filter(ServiceRequest.reference == reference).first()
    )
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    return request


@router.post(
    "/requests/{reference}/decision", response_model=RequestOut,
    dependencies=[Depends(verify_integration_key)],
)
def approval_decision(
    reference: str, payload: PowerPlatformDecision, db: Session = Depends(get_db),
) -> ServiceRequest:
    approver = db.query(User).filter(User.email == payload.approver_email).first()
    if not approver or approver.role not in {"approver", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approver not authorized")
    request = (
        db.query(ServiceRequest).filter(ServiceRequest.status != "draft")
        .options(joinedload(ServiceRequest.requester))
        .filter(ServiceRequest.reference == reference).first()
    )
    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    if request.requester_id == approver.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Users cannot approve their own request")
    if request.status != "pending_approval":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not pending approval")
    request.status = "in_progress" if payload.decision == "approve" else "rejected"
    db.add(Approval(request_id=request.id, approver_id=approver.id, decision=payload.decision, comment=payload.comment))
    add_audit_event(
        db, "power_automate_approval_decided", request=request, actor=approver,
        details={"decision": payload.decision, "comment": payload.comment},
    )
    db.commit()
    db.refresh(request)
    return request


@router.get(
    "/analytics-feed", response_model=list[AnalyticsFeedRow],
    dependencies=[Depends(verify_integration_key)],
)
def analytics_feed(
    limit: int = Query(default=500, ge=1, le=5000), db: Session = Depends(get_db),
) -> list[AnalyticsFeedRow]:
    now = datetime.now(UTC)
    rows = db.query(ServiceRequest).filter(ServiceRequest.status != "draft").order_by(ServiceRequest.submitted_at.desc()).limit(limit).all()
    return [AnalyticsFeedRow(
        reference=row.reference, title=row.title, department=row.department,
        category=row.category, priority=row.priority, status=row.status,
        submitted_at=row.submitted_at, due_at=row.due_at,
        completed_at=row.completed_at, ai_confidence=row.ai_confidence,
        within_sla=as_utc(row.completed_at or now) <= as_utc(row.due_at),
    ) for row in rows]
