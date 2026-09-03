from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.models import AutomationRun, KnowledgeArticle, ServiceRequest, User

USERS = [
    ("employee@centralops.demo", "Employee Demo", "Finance", "employee", "Employee123!"),
    ("other.employee@centralops.demo", "Other Employee", "Operations", "employee", "Employee123!"),
    ("approver@centralops.demo", "Approver Demo", "Central Service", "approver", "Approver123!"),
    ("admin@centralops.demo", "Admin Demo", "Technology", "admin", "Admin123!"),
]

ARTICLES = [
    (
        "request-priority-policy",
        "Service Request Priority Policy",
        "Urgent priority is reserved for business-critical outages, confirmed security risks, "
        "or incidents blocking a customer-facing operation. High priority covers significant "
        "degradation or work blocked for one or more employees. Medium is the default for normal "
        "requests, while low priority is used for planned or non-time-sensitive work.",
        "2.1",
    ),
    (
        "access-request-policy",
        "Access Request and Approval Policy",
        "Access requests must include the target application, requested role, business reason, "
        "manager, and required end date. Privileged access requires both line-manager and system-owner "
        "approval. Access must not be granted by the AI assistant; a named human approver owns the decision.",
        "1.4",
    ),
    (
        "service-sla-policy",
        "Central Service SLA Policy",
        "Urgent requests target a two-hour response, high priority eight hours, medium priority one "
        "business day, and low priority three business days. SLA timing begins when a complete request "
        "is submitted and pauses when required information is requested from the employee.",
        "3.0",
    ),
    (
        "procurement-policy",
        "Procurement Request Policy",
        "Procurement requests must include item specifications, quantity, cost estimate, business "
        "justification, and preferred delivery date. Purchases above the local approval threshold are "
        "routed to a budget owner before procurement review.",
        "1.8",
    ),
]


def seed_data(db: Session) -> None:
    if db.query(User).count() == 0:
        for email, name, department, role, password in USERS:
            db.add(
                User(
                    email=email,
                    full_name=name,
                    department=department,
                    role=role,
                    hashed_password=hash_password(password),
                )
            )
        db.commit()

    if db.query(KnowledgeArticle).count() == 0:
        for slug, title, content, version in ARTICLES:
            db.add(KnowledgeArticle(slug=slug, title=title, content=content, version=version))
        db.commit()

    if db.query(ServiceRequest).count() == 0:
        employee = db.query(User).filter(User.role == "employee").first()
        if not employee:
            return
        now = datetime.now(UTC)
        records = [
            (
                "VPN access for new finance analyst",
                "Access is required before Monday onboarding.",
                "access_request",
                "high",
                "pending_approval",
                0.96,
            ),
            (
                "Replace damaged barcode scanner",
                "Warehouse scanner no longer reads labels.",
                "it_support",
                "high",
                "in_progress",
                0.91,
            ),
            (
                "Update payroll bank information",
                "Employee submitted a verified bank change.",
                "hr_support",
                "medium",
                "completed",
                0.94,
            ),
            (
                "Air conditioning issue - meeting room 4B",
                "Room temperature affects scheduled meetings.",
                "facility",
                "medium",
                "in_progress",
                0.89,
            ),
            (
                "Purchase approval for team headsets",
                "Request includes three standard headsets.",
                "procurement",
                "low",
                "rejected",
                0.93,
            ),
        ]
        for index, (title, description, category, priority, status, confidence) in enumerate(
            records, 1
        ):
            submitted = now - timedelta(hours=index * 4)
            request = ServiceRequest(
                reference=f"CSR-{1049 - index}",
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=status,
                department=employee.department,
                requester_id=employee.id,
                assigned_to="Central Service Approver",
                ai_summary=f"{title}. {description}",
                ai_category=category,
                ai_priority=priority,
                ai_confidence=confidence,
                ai_model="deterministic-fallback-v1",
                submitted_at=submitted,
                due_at=submitted + timedelta(hours={"low": 72, "medium": 24, "high": 8}[priority]),
                completed_at=submitted + timedelta(hours=5) if status == "completed" else None,
            )
            db.add(request)
        db.add_all(
            [
                AutomationRun(
                    workflow_name="ai_triage", status="success", duration_ms=14, provider="mock"
                ),
                AutomationRun(
                    workflow_name="approval_routing",
                    status="success",
                    duration_ms=22,
                    provider="internal",
                ),
                AutomationRun(
                    workflow_name="policy_assistant",
                    status="success",
                    duration_ms=11,
                    provider="mock",
                ),
            ]
        )
        db.commit()
