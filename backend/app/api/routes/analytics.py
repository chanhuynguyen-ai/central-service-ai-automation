from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import require_roles
from app.db.session import get_db
from app.models.models import AutomationRun, ServiceRequest, User
from app.schemas.schemas import AnalyticsSummary, CategoryMetric

router = APIRouter()


@router.get("/summary", response_model=AnalyticsSummary)
def summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("approver", "admin")),
) -> AnalyticsSummary:
    # Legacy workload only; structured requests have a separate approval lifecycle.
    requests = db.query(ServiceRequest).filter(ServiceRequest.request_type_version_id.is_(None))
    total = requests.count()
    completed = requests.filter(ServiceRequest.status == "completed").count()
    pending = requests.filter(ServiceRequest.status == "pending_approval").count()
    open_requests = requests.filter(ServiceRequest.status.in_(["pending_approval", "in_progress"])).count()
    within_sla = requests.filter(
        (ServiceRequest.completed_at.is_not(None) & (ServiceRequest.completed_at <= ServiceRequest.due_at))
        | (ServiceRequest.completed_at.is_(None) & (ServiceRequest.due_at >= datetime.now(UTC)))
    ).count()
    triaged = requests.filter(ServiceRequest.ai_summary.is_not(None)).count()
    automation_total = db.query(AutomationRun).count()
    automation_success = db.query(AutomationRun).filter(AutomationRun.status == "success").count()
    category_rows = (
        db.query(ServiceRequest.category, func.count(ServiceRequest.id))
        .filter(ServiceRequest.request_type_version_id.is_(None))
        .group_by(ServiceRequest.category)
        .order_by(func.count(ServiceRequest.id).desc())
        .all()
    )
    return AnalyticsSummary(
        total_requests=total,
        open_requests=open_requests,
        pending_approvals=pending,
        completed_requests=completed,
        sla_compliance_rate=round((within_sla / total * 100) if total else 100.0, 1),
        automation_success_rate=round((automation_success / automation_total * 100) if automation_total else 100.0, 1),
        ai_triage_coverage=round((triaged / total * 100) if total else 0.0, 1),
        category_breakdown=[CategoryMetric(category=row[0], count=row[1]) for row in category_rows],
    )
