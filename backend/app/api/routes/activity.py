from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.api.routes.workflows import transaction
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.activity import RequestComment, RequestEvent
from app.models.models import User
from app.schemas.activity import (
    ActivityPermissions,
    CommentCreate,
    CommentOut,
    CommentPage,
    EventOut,
    EventPage,
    Visibility,
)
from app.services import activity
from app.services.audit import safe_details
from app.services.workflows import WorkflowError

router = APIRouter()


def _request(db, actor, request_id):
    try:
        return activity.scoped_request(db, actor, request_id)
    except WorkflowError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.get("/requests/{request_id}/permissions", response_model=ActivityPermissions)
def read_permissions(request_id: int, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return activity.permissions(db, actor, _request(db, actor, request_id))


@router.get("/requests/{request_id}/timeline", response_model=EventPage)
def timeline(request_id: int, before_id: int | None = Query(default=None, ge=1),
             limit: int = Query(default=30, ge=1, le=100), db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    request = _request(db, actor, request_id)
    query = activity.event_query(db, actor, request)
    if before_id is not None:
        query = query.filter(RequestEvent.id < before_id)
    rows = query.order_by(RequestEvent.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    items = []
    for row in rows:
        user = db.get(User, row.actor_id) if row.actor_id else None
        items.append(EventOut(id=row.id, request_id=row.request_id, actor_id=row.actor_id,
                    actor_name=user.full_name if user else None, event_type=row.event_type,
                    visibility=row.visibility, payload=safe_details(row.payload), created_at=row.created_at))
    return EventPage(items=items, next_before_id=rows[-1].id if more else None)


@router.get("/requests/{request_id}/comments", response_model=CommentPage)
def comments(request_id: int, visibility: Visibility = "REQUESTER_VISIBLE",
             before_id: int | None = Query(default=None, ge=1), limit: int = Query(default=30, ge=1, le=100),
             db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    request = _request(db, actor, request_id)
    if visibility == "INTERNAL" and not activity.permissions(db, actor, request).can_read_internal:
        raise HTTPException(403, "Internal notes are restricted")
    query = db.query(RequestComment).filter_by(request_id=request.id, visibility=visibility)
    if before_id is not None:
        query = query.filter(RequestComment.id < before_id)
    rows = query.order_by(RequestComment.id.desc()).limit(limit + 1).all()
    more = len(rows) > limit
    rows = rows[:limit]
    return CommentPage(items=[activity.comment_output(db, row) for row in rows], next_before_id=rows[-1].id if more else None)


@router.post("/requests/{request_id}/comments", response_model=CommentOut, status_code=201)
def post_comment(request_id: int, payload: CommentCreate, response: Response,
                 db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    with transaction(db):
        comment, created = activity.add_comment(db, actor, request_id, payload)
        response.status_code = 201 if created else 200
        return activity.comment_output(db, comment)
