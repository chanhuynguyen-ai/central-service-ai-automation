from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.models import (
    AutomationRun,
    Department,
    KnowledgeArticle,
    Role,
    ServiceRequest,
    ServiceTeam,
    ServiceTeamMember,
    User,
    UserRole,
)

DEPARTMENTS = {
    "FINANCE": "Finance",
    "OPERATIONS": "Operations",
    "CENTRAL_SERVICE": "Central Service",
    "TECHNOLOGY": "Technology",
}


ROLES = {
    "EMPLOYEE": (
        "Employee",
        "Standard employee who creates and follows service requests.",
    ),
    "APPROVER": (
        "Approver",
        "User allowed to act on assigned approval tasks.",
    ),
    "MANAGER": (
        "Manager",
        "Line manager who participates in manager approval workflows.",
    ),
    "SERVICE_AGENT": (
        "Service Agent",
        "Agent responsible for fulfilling service work.",
    ),
    "SERVICE_LEAD": (
        "Service Lead",
        "Lead responsible for a service team and escalated work.",
    ),
    "ADMIN": (
        "Administrator",
        "System administrator with privileged configuration access.",
    ),
    "AUDITOR": (
        "Auditor",
        "Read-oriented role for audit and governance activities.",
    ),
}


USERS = [
    {
        "email": "employee@centralops.demo",
        "name": "Employee Demo",
        "department": "FINANCE",
        "legacy_role": "employee",
        "password": "Employee123!",
        "roles": ["EMPLOYEE"],
    },
    {
        "email": "other.employee@centralops.demo",
        "name": "Other Employee",
        "department": "OPERATIONS",
        "legacy_role": "employee",
        "password": "Employee123!",
        "roles": ["EMPLOYEE"],
    },
    {
        "email": "approver@centralops.demo",
        "name": "Approver Demo",
        "department": "CENTRAL_SERVICE",
        "legacy_role": "approver",
        "password": "Approver123!",
        "roles": ["APPROVER"],
    },
    {
        "email": "admin@centralops.demo",
        "name": "Admin Demo",
        "department": "TECHNOLOGY",
        "legacy_role": "admin",
        "password": "Admin123!",
        "roles": ["ADMIN"],
    },
    {
        "email": "manager.finance@centralops.demo",
        "name": "Finance Manager",
        "department": "FINANCE",
        "legacy_role": "manager",
        "password": "Manager123!",
        "roles": ["EMPLOYEE", "MANAGER", "APPROVER"],
    },
    {
        "email": "manager.operations@centralops.demo",
        "name": "Operations Manager",
        "department": "OPERATIONS",
        "legacy_role": "manager",
        "password": "Manager123!",
        "roles": ["EMPLOYEE", "MANAGER", "APPROVER"],
    },
    {
        "email": "service.lead@centralops.demo",
        "name": "Central Service Lead",
        "department": "CENTRAL_SERVICE",
        "legacy_role": "service_lead",
        "password": "ServiceLead123!",
        "roles": ["SERVICE_LEAD", "APPROVER"],
    },
    {
        "email": "service.agent@centralops.demo",
        "name": "Central Service Agent",
        "department": "CENTRAL_SERVICE",
        "legacy_role": "service_agent",
        "password": "ServiceAgent123!",
        "roles": ["SERVICE_AGENT"],
    },
    {
        "email": "auditor@centralops.demo",
        "name": "Auditor Demo",
        "department": "TECHNOLOGY",
        "legacy_role": "auditor",
        "password": "Auditor123!",
        "roles": ["AUDITOR"],
    },
]


MANAGERS = {
    "employee@centralops.demo": "manager.finance@centralops.demo",
    "other.employee@centralops.demo": "manager.operations@centralops.demo",
    "approver@centralops.demo": "service.lead@centralops.demo",
    "service.agent@centralops.demo": "service.lead@centralops.demo",
}


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
        "manager, and required end date. Privileged access requires both line-manager and "
        "system-owner approval. Access must not be granted by the AI assistant; a named human "
        "approver owns the decision.",
        "1.4",
    ),
    (
        "service-sla-policy",
        "Central Service SLA Policy",
        "Urgent requests target a two-hour response, high priority eight hours, medium priority "
        "one business day, and low priority three business days. SLA timing begins when a complete "
        "request is submitted and pauses when required information is requested from the employee.",
        "3.0",
    ),
    (
        "procurement-policy",
        "Procurement Request Policy",
        "Procurement requests must include item specifications, quantity, cost estimate, "
        "business justification, and preferred delivery date. Purchases above the local approval "
        "threshold are routed to a budget owner before procurement review.",
        "1.8",
    ),
]


def _ensure_departments(db: Session) -> dict[str, Department]:
    departments: dict[str, Department] = {}

    for code, name in DEPARTMENTS.items():
        department = (
            db.query(Department)
            .filter(Department.code == code)
            .first()
        )

        if department is None:
            department = Department(
                code=code,
                name=name,
                is_active=True,
            )
            db.add(department)
            db.flush()
        else:
            department.name = name
            department.is_active = True

        departments[code] = department

    return departments


def _ensure_roles(db: Session) -> dict[str, Role]:
    roles: dict[str, Role] = {}

    for code, (name, description) in ROLES.items():
        role = (
            db.query(Role)
            .filter(Role.code == code)
            .first()
        )

        if role is None:
            role = Role(
                code=code,
                name=name,
                description=description,
                is_system=True,
            )
            db.add(role)
            db.flush()
        else:
            role.name = name
            role.description = description
            role.is_system = True

        roles[code] = role

    return roles


def _ensure_users(
    db: Session,
    departments: dict[str, Department],
) -> dict[str, User]:
    users: dict[str, User] = {}

    for definition in USERS:
        department = departments[definition["department"]]

        user = (
            db.query(User)
            .filter(User.email == definition["email"])
            .first()
        )

        if user is None:
            user = User(
                email=definition["email"],
                full_name=definition["name"],
                department=department.name,
                role=definition["legacy_role"],
                department_id=department.id,
                hashed_password=hash_password(definition["password"]),
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.full_name = definition["name"]
            user.department = department.name
            user.role = definition["legacy_role"]
            user.department_id = department.id

        users[definition["email"]] = user

    return users


def _ensure_role_assignments(
    db: Session,
    users: dict[str, User],
    roles: dict[str, Role],
) -> None:
    for definition in USERS:
        user = users[definition["email"]]

        for role_code in definition["roles"]:
            role = roles[role_code]

            assignment = (
                db.query(UserRole)
                .filter(
                    UserRole.user_id == user.id,
                    UserRole.role_id == role.id,
                )
                .first()
            )

            if assignment is None:
                db.add(
                    UserRole(
                        user_id=user.id,
                        role_id=role.id,
                    )
                )


def _ensure_manager_hierarchy(
    users: dict[str, User],
) -> None:
    for employee_email, manager_email in MANAGERS.items():
        employee = users[employee_email]
        manager = users[manager_email]
        employee.manager_id = manager.id


def _ensure_central_service_team(
    db: Session,
    departments: dict[str, Department],
    users: dict[str, User],
) -> None:
    lead = users["service.lead@centralops.demo"]
    department = departments["CENTRAL_SERVICE"]

    team = (
        db.query(ServiceTeam)
        .filter(ServiceTeam.code == "CENTRAL_SERVICE")
        .first()
    )

    if team is None:
        team = ServiceTeam(
            code="CENTRAL_SERVICE",
            name="Central Service",
            department_id=department.id,
            lead_user_id=lead.id,
            is_active=True,
        )
        db.add(team)
        db.flush()
    else:
        team.name = "Central Service"
        team.department_id = department.id
        team.lead_user_id = lead.id
        team.is_active = True

    member_emails = (
        "service.lead@centralops.demo",
        "approver@centralops.demo",
        "service.agent@centralops.demo",
    )

    for email in member_emails:
        user = users[email]

        membership = (
            db.query(ServiceTeamMember)
            .filter(
                ServiceTeamMember.service_team_id == team.id,
                ServiceTeamMember.user_id == user.id,
            )
            .first()
        )

        if membership is None:
            db.add(
                ServiceTeamMember(
                    service_team_id=team.id,
                    user_id=user.id,
                )
            )


def _ensure_organization(db: Session) -> dict[str, User]:
    departments = _ensure_departments(db)
    roles = _ensure_roles(db)
    users = _ensure_users(db, departments)

    _ensure_role_assignments(
        db,
        users,
        roles,
    )
    _ensure_manager_hierarchy(users)
    _ensure_central_service_team(
        db,
        departments,
        users,
    )

    db.commit()

    return users


def seed_data(db: Session) -> None:
    users = _ensure_organization(db)

    if db.query(KnowledgeArticle).count() == 0:
        for slug, title, content, version in ARTICLES:
            db.add(
                KnowledgeArticle(
                    slug=slug,
                    title=title,
                    content=content,
                    version=version,
                )
            )

        db.commit()

    if db.query(ServiceRequest).count() == 0:
        employee = users["employee@centralops.demo"]
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

        for index, (
            title,
            description,
            category,
            priority,
            request_status,
            confidence,
        ) in enumerate(records, 1):
            submitted = now - timedelta(hours=index * 4)

            request = ServiceRequest(
                reference=f"CSR-{1049 - index}",
                title=title,
                description=description,
                category=category,
                priority=priority,
                status=request_status,
                department=employee.department,
                requester_id=employee.id,
                assigned_to="Central Service Approver",
                ai_summary=f"{title}. {description}",
                ai_category=category,
                ai_priority=priority,
                ai_confidence=confidence,
                ai_model="deterministic-fallback-v1",
                submitted_at=submitted,
                due_at=submitted
                + timedelta(
                    hours={
                        "low": 72,
                        "medium": 24,
                        "high": 8,
                    }[priority]
                ),
                completed_at=(
                    submitted + timedelta(hours=5)
                    if request_status == "completed"
                    else None
                ),
            )
            db.add(request)

        db.add_all(
            [
                AutomationRun(
                    workflow_name="ai_triage",
                    status="success",
                    duration_ms=14,
                    provider="mock",
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