from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.models import AutomationRun, User
from app.schemas.schemas import AutomationRunOut

router = APIRouter()


@router.get("/runs", response_model=list[AutomationRunOut])
def list_runs(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("approver", "admin")),
) -> list[AutomationRun]:
    return db.query(AutomationRun).order_by(AutomationRun.created_at.desc()).limit(limit).all()
