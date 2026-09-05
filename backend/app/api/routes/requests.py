from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import Approval, ServiceRequest, User
from app.schemas.schemas import DecisionInput, RequestCreate, RequestList, RequestOut, StatusUpdate
from app.services.llm import ai_service
from app.services.permissions import (
    can_change_request_status,
    can_decide_approval,
    can_view_all_requests,
    can_view_direct_reports,
    can_view_request,
)
from app.services.workflow import add_audit_event, create_request

router = APIRouter()


def get_visible_request(db: Session, request_id: int, user: User) -> ServiceRequest:
    query = db.query(ServiceRequest).filter(ServiceRequest.request_type_version_id.is_(None)).options(joinedload(ServiceRequest.requester))
    request = query.filter(ServiceRequest.id == request_id).first()

    if not request or not can_view_request(user, request):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return request


@router.get("", response_model=RequestList)
def list_requests(
    request_status: str | None = Query(default=None, alias="status"),
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> RequestList:
    query = db.query(ServiceRequest).filter(ServiceRequest.request_type_version_id.is_(None)).options(joinedload(ServiceRequest.requester))

    if not can_view_all_requests(user):
        if can_view_direct_reports(user):
            query = query.join(User, ServiceRequest.requester_id == User.id).filter(
                or_(ServiceRequest.requester_id == user.id, User.manager_id == user.id)
            )
        else:
            query = query.filter(ServiceRequest.requester_id == user.id)

    if request_status:
        query = query.filter(ServiceRequest.status == request_status)
    if category:
        query = query.filter(ServiceRequest.category == category)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(ServiceRequest.reference.ilike(term), ServiceRequest.title.ilike(term))
        )
    total = query.count()
    items = query.order_by(ServiceRequest.submitted_at.desc()).offset(offset).limit(limit).all()
    return RequestList(items=[RequestOut.model_validate(item) for item in items], total=total)


@router.post("", response_model=RequestOut, status_code=status.HTTP_201_CREATED)
def submit_request(
    payload: RequestCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRequest:
    triage = ai_service.triage(db, payload.title, payload.description)
    request = create_request(db, payload, user, triage)
    db.commit()
    db.refresh(request)
    return request


@router.get("/{request_id}", response_model=RequestOut)
def request_detail(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ServiceRequest:
    return get_visible_request(db, request_id, user)


@router.post("/{request_id}/decision", response_model=RequestOut)
def decide_request(
    request_id: int,
    payload: DecisionInput,
    db: Session = Depends(get_db),
    approver: User = Depends(require_roles("APPROVER", "ADMIN")),
) -> ServiceRequest:
    request = get_visible_request(db, request_id, approver)
    if not can_decide_approval(approver, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to decide this request",
        )
    if request.status != "pending_approval":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is not pending approval")
    request.status = "in_progress" if payload.decision == "approve" else "rejected"
    db.add(Approval(
        request_id=request.id, approver_id=approver.id,
        decision=payload.decision, comment=payload.comment,
    ))
    add_audit_event(
        db, "approval_decided", request=request, actor=approver,
        details={"decision": payload.decision, "comment": payload.comment},
    )
    db.commit()
    db.refresh(request)
    return request


@router.patch("/{request_id}/status", response_model=RequestOut)
def update_status(
    request_id: int,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
    operator: User = Depends(require_roles("APPROVER", "SERVICE_LEAD", "ADMIN")),
) -> ServiceRequest:
    request = get_visible_request(db, request_id, operator)
    if not can_change_request_status(operator, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to change request status",
        )
    previous = request.status
    request.status = payload.status
    if payload.status == "completed":
        request.completed_at = datetime.now(UTC)
    add_audit_event(
        db, "status_changed", request=request, actor=operator,
        details={"from": previous, "to": payload.status, "comment": payload.comment},
    )
    db.commit()
    db.refresh(request)
    return request
