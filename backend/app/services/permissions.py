from app.models.models import ServiceRequest, User

GLOBAL_REQUEST_VIEW_ROLES = frozenset(
    {
        "ADMIN",
        "AUDITOR",
        "SERVICE_LEAD",
    }
)

APPROVAL_DECISION_ROLES = frozenset(
    {
        "ADMIN",
        "APPROVER",
    }
)

REQUEST_STATUS_CHANGE_ROLES = frozenset(
    {
        "ADMIN",
        "APPROVER",
        "SERVICE_LEAD",
    }
)


def normalize_role_code(role_code: str) -> str:
    return role_code.strip().replace("-", "_").replace(" ", "_").upper()


def user_role_codes(user: User) -> frozenset[str]:
    """Return normalized RBAC roles plus the temporary legacy fallback."""
    role_codes: set[str] = set()

    if user.role:
        role_codes.add(normalize_role_code(user.role))

    for assignment in user.role_assignments:
        if assignment.role and assignment.role.code:
            role_codes.add(normalize_role_code(assignment.role.code))

    return frozenset(role_codes)


def user_has_role(user: User, role: str) -> bool:
    return normalize_role_code(role) in user_role_codes(user)


def user_has_any_role(user: User, *roles: str) -> bool:
    expected = {normalize_role_code(role) for role in roles}
    return bool(user_role_codes(user) & expected)


def can_view_all_requests(user: User) -> bool:
    """
    Return whether the actor currently has organization-wide request visibility.

    APPROVER is temporarily broad only for the standalone prototype approver.

    If the same user is also a MANAGER, manager scope takes precedence:
    the manager sees only their own requests and requests from direct reports.

    Once Phase 5 introduces approval_tasks, the broad APPROVER fallback
    should be removed. Approvers will then see only requests tied to their
    assigned current/past approval tasks.
    """
    roles = user_role_codes(user)

    if roles & GLOBAL_REQUEST_VIEW_ROLES:
        return True

    return "APPROVER" in roles and "MANAGER" not in roles


def can_view_direct_reports(user: User) -> bool:
    return user_has_role(user, "MANAGER")


def can_view_request(actor: User, request: ServiceRequest) -> bool:
    if request.requester_id == actor.id:
        return True

    if can_view_all_requests(actor):
        return True

    if can_view_direct_reports(actor):
        requester = request.requester
        return requester.manager_id == actor.id

    return False


def can_decide_approval(actor: User, request: ServiceRequest) -> bool:
    if request.requester_id == actor.id:
        return False

    return bool(user_role_codes(actor) & APPROVAL_DECISION_ROLES)


def can_change_request_status(actor: User, request: ServiceRequest) -> bool:
    del request
    return bool(user_role_codes(actor) & REQUEST_STATUS_CHANGE_ROLES)