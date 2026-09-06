from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.notifications import NotificationOut, NotificationPage
from app.services import notifications as service

router = APIRouter()


@router.get("", response_model=NotificationPage)
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    return service.list_in_app(
        db,
        actor,
        unread_only=unread_only,
        limit=limit,
        offset=offset,
    )


@router.post("/{notification_id}/read", response_model=NotificationOut)
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    try:
        row = service.mark_read(db, actor, notification_id)
        db.commit()
        return row
    except service.NotificationError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/read-all")
def read_all_notifications(
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    count = service.mark_all_read(db, actor)
    db.commit()
    return {"updated": count}
