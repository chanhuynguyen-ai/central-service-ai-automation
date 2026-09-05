from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import Department, ServiceRequest, User
from app.schemas.drafts import DraftCreate, DraftList, DraftOut, DraftUpdate, DraftValidation
from app.services.drafts import (
    DraftError,
    create_draft,
    draft_output,
    owned_draft,
    update_draft,
)

router = APIRouter()


@router.get("", response_model=DraftList)
def list_drafts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> DraftList:
    query = db.query(ServiceRequest).filter(
        ServiceRequest.requester_id == actor.id, ServiceRequest.status == "draft",
    )
    total = query.count()
    rows = query.order_by(ServiceRequest.updated_at.desc(), ServiceRequest.id.desc()).offset(offset).limit(limit).all()
    try:
        return DraftList(items=[draft_output(db, row) for row in rows], total=total)
    except DraftError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
def new_draft(
    payload: DraftCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> DraftOut:
    try:
        draft = create_draft(db, actor, payload)
        output = draft_output(db, draft)
        db.commit()
        return output
    except DraftError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/lookups")
def draft_lookups(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> dict:
    # MVP organization directory: identifiers/names only, no email or role data.
    del actor
    users = db.query(User).filter(User.is_active.is_(True)).order_by(User.full_name, User.id).limit(500).all()
    departments = db.query(Department).filter(Department.is_active.is_(True)).order_by(Department.name, Department.id).limit(500).all()
    return {
        "users": [{"id": user.id, "name": user.full_name} for user in users],
        "departments": [{"id": department.id, "name": department.name} for department in departments],
    }


@router.get("/{request_id}", response_model=DraftOut)
def read_draft(
    request_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> DraftOut:
    try:
        return draft_output(db, owned_draft(db, request_id, actor))
    except DraftError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.put("/{request_id}", response_model=DraftOut)
def save_draft(
    request_id: int,
    payload: DraftUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> DraftOut:
    try:
        draft = update_draft(db, actor, request_id, payload)
        output = draft_output(db, draft)
        db.commit()
        return output
    except DraftError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{request_id}/validate", response_model=DraftValidation)
def check_draft(
    request_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> DraftValidation:
    try:
        return draft_output(db, owned_draft(db, request_id, actor)).validation
    except DraftError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
