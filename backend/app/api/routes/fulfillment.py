from collections.abc import Generator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.fulfillment import WorkItemAction, WorkItemOut
from app.services import fulfillment as service

router = APIRouter()


@contextmanager
def transaction(db: Session) -> Generator[None, None, None]:
    try:
        yield
        db.commit()
    except service.FulfillmentError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Conflicting fulfillment operation; reload and retry.") from exc


@router.get("/work-items")
def list_items(
    scope: str = Query(default="team", pattern="^(team|unassigned|mine)$"),
    status: str | None = Query(default=None, pattern="^(QUEUED|ASSIGNED|IN_PROGRESS|WAITING_REQUESTER|RESOLVED|CLOSED)$"),
    limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    try:
        return service.list_work_items(db, actor, scope, status, limit, offset)
    except service.FulfillmentError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/work-items/{item_id}/actions", response_model=WorkItemOut)
def act_on_item(
    item_id: int, payload: WorkItemAction,
    db: Session = Depends(get_db), actor: User = Depends(get_current_user),
):
    with transaction(db):
        item, request = service.act(db, actor, item_id, payload)
        return WorkItemOut.model_validate(service.work_item_output(db, item, request, actor))
