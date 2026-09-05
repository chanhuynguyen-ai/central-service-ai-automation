"""Authorized service queue and deterministic fulfillment state machine."""
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.fulfillment import ServiceWorkItem
from app.models.models import ServiceRequest, ServiceTeam, ServiceTeamMember, User
from app.schemas.fulfillment import WorkItemAction
from app.services.audit import record_audit
from app.services.permissions import user_has_any_role


class FulfillmentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _member_team_ids(db: Session, actor: User) -> list[int]:
    ids = list(
        db.scalars(
            select(ServiceTeamMember.service_team_id)
            .join(ServiceTeam, ServiceTeam.id == ServiceTeamMember.service_team_id)
            .where(
                ServiceTeamMember.user_id == actor.id,
                ServiceTeam.is_active.is_(True),
            )
        )
    )
    ids.extend(
        db.scalars(
            select(ServiceTeam.id).where(
                ServiceTeam.lead_user_id == actor.id,
                ServiceTeam.is_active.is_(True),
            )
        )
    )
    return sorted(set(ids))


def _is_service_worker(db: Session, actor: User, team_id: int) -> bool:
    if not actor.is_active:
        return False
    if user_has_any_role(actor, "ADMIN"):
        return True
    if not user_has_any_role(actor, "SERVICE_AGENT", "SERVICE_LEAD"):
        return False
    return team_id in _member_team_ids(db, actor)


def _is_team_lead_or_admin(db: Session, actor: User, team_id: int) -> bool:
    if user_has_any_role(actor, "ADMIN"):
        return True
    team = db.get(ServiceTeam, team_id)
    return bool(
        team
        and team.is_active
        and team.lead_user_id == actor.id
        and user_has_any_role(actor, "SERVICE_LEAD")
    )


def _can_operate_assigned(db: Session, actor: User, item: ServiceWorkItem) -> bool:
    return bool(
        item.assignee_user_id == actor.id
        or _is_team_lead_or_admin(db, actor, item.service_team_id)
    )


def _team_from_snapshot(snapshot: dict) -> int | None:
    direct = snapshot.get("owner_service_team_id")
    if type(direct) is int:
        return direct
    workflow = snapshot.get("workflow") if isinstance(snapshot.get("workflow"), dict) else {}
    for step in reversed(workflow.get("steps", [])):
        if not isinstance(step, dict) or step.get("approver_resolver_type") != "TEAM_LEAD":
            continue
        config = step.get("approver_resolver_config")
        team_id = config.get("service_team_id") if isinstance(config, dict) else None
        if type(team_id) is int:
            return team_id
    return None


def ensure_work_item(
    db: Session,
    request: ServiceRequest,
    snapshot: dict,
    actor: User,
) -> ServiceWorkItem:
    existing = db.query(ServiceWorkItem).filter_by(request_id=request.id).first()
    if existing:
        return existing
    team_id = _team_from_snapshot(snapshot)
    team = db.get(ServiceTeam, team_id) if team_id else None
    if not team or not team.is_active:
        raise FulfillmentError(
            409,
            "Final approval cannot queue fulfillment: no active owner service team is configured.",
        )
    if request.status != "approved" or request.approval_state != "approved":
        raise FulfillmentError(409, "Only finally approved requests can enter fulfillment")
    item = ServiceWorkItem(
        request_id=request.id,
        service_team_id=team.id,
        status="QUEUED",
    )
    db.add(item)
    db.flush()
    request.fulfillment_state = "queued"
    request.updated_at = datetime.now(UTC)
    record_audit(
        db,
        "service_queued",
        actor_id=actor.id,
        request_id=request.id,
        resource_type="service_work_item",
        resource_id=str(item.id),
        details={"work_item_id": item.id, "service_team_id": team.id},
        domain=True,
    )
    db.flush()
    return item


def queue_query(db: Session, actor: User):
    query = db.query(ServiceWorkItem, ServiceRequest).join(
        ServiceRequest,
        ServiceWorkItem.request_id == ServiceRequest.id,
    )
    if user_has_any_role(actor, "ADMIN"):
        return query
    team_ids = _member_team_ids(db, actor)
    if not team_ids or not user_has_any_role(actor, "SERVICE_AGENT", "SERVICE_LEAD"):
        raise FulfillmentError(
            403,
            "Service queue access requires an authorized service-team role",
        )
    return query.filter(ServiceWorkItem.service_team_id.in_(team_ids))


def work_item_output(
    db: Session,
    item: ServiceWorkItem,
    request: ServiceRequest,
    actor: User,
) -> dict:
    team = db.get(ServiceTeam, item.service_team_id)
    assignee = db.get(User, item.assignee_user_id) if item.assignee_user_id else None
    return {
        "id": item.id,
        "request_id": request.id,
        "reference": request.reference,
        "title": request.title,
        "requester_name": request.requester.full_name,
        "service_team_id": item.service_team_id,
        "service_team_name": team.name if team else "Unknown team",
        "assignee_user_id": item.assignee_user_id,
        "assignee_name": assignee.full_name if assignee else None,
        "status": item.status,
        "version": item.version,
        "resolution_summary": item.resolution_summary,
        "queued_at": item.queued_at,
        "assigned_at": item.assigned_at,
        "started_at": item.started_at,
        "waiting_at": item.waiting_at,
        "resolved_at": item.resolved_at,
        "closed_at": item.closed_at,
        "due_at": item.due_at,
        "can_manage": _is_service_worker(db, actor, item.service_team_id),
    }


def list_work_items(
    db: Session,
    actor: User,
    scope: str,
    status: str | None,
    limit: int,
    offset: int,
) -> dict:
    query = queue_query(db, actor)
    if scope == "unassigned":
        query = query.filter(
            ServiceWorkItem.assignee_user_id.is_(None),
            ServiceWorkItem.status == "QUEUED",
        )
    elif scope == "mine":
        query = query.filter(ServiceWorkItem.assignee_user_id == actor.id)
    if status:
        query = query.filter(ServiceWorkItem.status == status)
    total = query.count()
    rows = (
        query.order_by(ServiceWorkItem.updated_at.desc(), ServiceWorkItem.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": [work_item_output(db, item, request, actor) for item, request in rows],
        "total": total,
    }


def _locked_item(
    db: Session,
    actor: User,
    item_id: int,
) -> tuple[ServiceWorkItem, ServiceRequest]:
    row = (
        db.query(ServiceWorkItem, ServiceRequest)
        .join(ServiceRequest, ServiceWorkItem.request_id == ServiceRequest.id)
        .filter(ServiceWorkItem.id == item_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if not row:
        raise FulfillmentError(404, "Service work item not found")
    item, request = row
    if not _is_service_worker(db, actor, item.service_team_id):
        raise FulfillmentError(403, "You are not authorized for this service team")
    return item, request


def _eligible_assignee(db: Session, team_id: int, user_id: int) -> User:
    user = db.get(User, user_id)
    if (
        not user
        or not user.is_active
        or not user_has_any_role(user, "SERVICE_AGENT", "SERVICE_LEAD")
    ):
        raise FulfillmentError(
            422,
            "Assignee must be an active service agent or service lead",
        )
    team = db.get(ServiceTeam, team_id)
    if not team or not team.is_active:
        raise FulfillmentError(409, "Service team is inactive")
    member = db.query(ServiceTeamMember).filter_by(
        service_team_id=team_id,
        user_id=user_id,
    ).first()
    if not member and team.lead_user_id != user_id:
        raise FulfillmentError(422, "Assignee is not a member of this service team")
    return user


def act(
    db: Session,
    actor: User,
    item_id: int,
    payload: WorkItemAction,
) -> tuple[ServiceWorkItem, ServiceRequest]:
    item, request = _locked_item(db, actor, item_id)
    db.refresh(item)
    if item.version != payload.version:
        raise FulfillmentError(409, "Work item changed. Reload before acting.")

    now = datetime.now(UTC)
    old_status = item.status
    new_status = old_status
    assignee_user_id = item.assignee_user_id
    assigned_at = item.assigned_at
    started_at = item.started_at
    waiting_at = item.waiting_at
    resolved_at = item.resolved_at
    closed_at = item.closed_at
    resolution_summary = item.resolution_summary
    event: str
    details: dict = {"work_item_id": item.id}

    if payload.action == "assign":
        target_id = payload.assignee_user_id or actor.id
        _eligible_assignee(db, item.service_team_id, target_id)
        if old_status not in {"QUEUED", "ASSIGNED"}:
            raise FulfillmentError(409, "Only queued or assigned work can be reassigned")
        if target_id != actor.id and not _is_team_lead_or_admin(
            db,
            actor,
            item.service_team_id,
        ):
            raise FulfillmentError(
                403,
                "Only the team lead or administrator can assign another agent",
            )
        assignee_user_id = target_id
        new_status = "ASSIGNED"
        assigned_at = now
        event = "service_assigned"
        details["assignee_user_id"] = target_id
    elif payload.action == "start":
        if old_status != "ASSIGNED":
            raise FulfillmentError(409, "Only assigned work can be started")
        if not _can_operate_assigned(db, actor, item):
            raise FulfillmentError(403, "Only the assignee or team lead can start this work")
        new_status = "IN_PROGRESS"
        started_at = started_at or now
        event = "service_started"
    elif payload.action == "wait":
        if old_status != "IN_PROGRESS":
            raise FulfillmentError(409, "Only in-progress work can wait for requester")
        if not _can_operate_assigned(db, actor, item):
            raise FulfillmentError(403, "Only the assignee or team lead can update this work")
        new_status = "WAITING_REQUESTER"
        waiting_at = now
        event = "service_waiting_requester"
    elif payload.action == "resume":
        if old_status != "WAITING_REQUESTER":
            raise FulfillmentError(409, "Only requester-waiting work can resume")
        if not _can_operate_assigned(db, actor, item):
            raise FulfillmentError(403, "Only the assignee or team lead can update this work")
        new_status = "IN_PROGRESS"
        event = "service_resumed"
    elif payload.action == "resolve":
        if old_status not in {"IN_PROGRESS", "WAITING_REQUESTER"}:
            raise FulfillmentError(409, "Only active work can be resolved")
        if not _can_operate_assigned(db, actor, item):
            raise FulfillmentError(403, "Only the assignee or team lead can resolve this work")
        new_status = "RESOLVED"
        resolved_at = now
        resolution_summary = (payload.note or "").strip()
        event = "request_resolved"
    elif payload.action == "close":
        if old_status != "RESOLVED":
            raise FulfillmentError(409, "Only resolved work can be closed")
        if not _can_operate_assigned(db, actor, item):
            raise FulfillmentError(403, "Only the assignee or team lead can close this work")
        new_status = "CLOSED"
        closed_at = now
        event = "request_closed"
    else:
        raise FulfillmentError(422, "Unsupported fulfillment action")

    changed = db.execute(
        update(ServiceWorkItem)
        .where(
            ServiceWorkItem.id == item.id,
            ServiceWorkItem.version == payload.version,
            ServiceWorkItem.status == old_status,
        )
        .values(
            status=new_status,
            assignee_user_id=assignee_user_id,
            assigned_at=assigned_at,
            started_at=started_at,
            waiting_at=waiting_at,
            resolved_at=resolved_at,
            closed_at=closed_at,
            resolution_summary=resolution_summary,
            version=payload.version + 1,
            updated_at=now,
        )
        .execution_options(synchronize_session=False)
    )
    if changed.rowcount != 1:
        raise FulfillmentError(
            409,
            "Work item changed while acting. Reload before retrying.",
        )
    db.refresh(item)

    request.fulfillment_state = item.status.lower()
    if item.status in {"IN_PROGRESS", "WAITING_REQUESTER"}:
        request.status = "in_progress"
    elif item.status == "RESOLVED":
        request.status = "resolved"
    elif item.status == "CLOSED":
        request.status = "completed"
        request.completed_at = now
    request.updated_at = now
    record_audit(
        db,
        event,
        actor_id=actor.id,
        request_id=request.id,
        resource_type="service_work_item",
        resource_id=str(item.id),
        details={
            **details,
            "from_status": old_status,
            "to_status": item.status,
        },
        domain=True,
    )
    db.flush()
    return item, request
