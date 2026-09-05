from app.models.fulfillment import ServiceWorkItem
from app.models.models import ServiceTeam, User
from app.schemas.fulfillment import WorkItemAction
from app.services.fulfillment import FulfillmentError, act, ensure_work_item, list_work_items


def _user(db, email):
    return db.query(User).filter_by(email=email).first()


def _approved_request(db):
    from app.models.models import ServiceRequest
    requester = _user(db, "employee@centralops.demo")
    request = ServiceRequest(reference="FUL-1", title="Fulfillment test", description="Approved work", category="IT",
                             priority="medium", status="approved", department=requester.department,
                             requester_id=requester.id, approval_state="approved", fulfillment_state="not_queued",
                             workflow_attempt=1)
    db.add(request)
    db.flush()
    return request


def test_approved_request_queues_exactly_once(db_session):
    db = db_session
    request = _approved_request(db)
    lead = _user(db, "service.lead@centralops.demo")
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").first()
    snapshot = {"owner_service_team_id": team.id}
    first = ensure_work_item(db, request, snapshot, lead)
    second = ensure_work_item(db, request, snapshot, lead)
    assert first.id == second.id
    assert db.query(ServiceWorkItem).filter_by(request_id=request.id).count() == 1
    assert request.fulfillment_state == "queued"


def test_service_agent_can_claim_and_complete_state_machine(db_session):
    db = db_session
    request = _approved_request(db)
    lead = _user(db, "service.lead@centralops.demo")
    agent = _user(db, "service.agent@centralops.demo")
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").first()
    item = ensure_work_item(db, request, {"owner_service_team_id": team.id}, lead)
    item, request = act(db, agent, item.id, WorkItemAction(action="assign", version=item.version))
    assert item.assignee_user_id == agent.id and item.status == "ASSIGNED"
    item, request = act(db, agent, item.id, WorkItemAction(action="start", version=item.version))
    assert item.status == "IN_PROGRESS" and request.status == "in_progress"
    item, request = act(db, agent, item.id, WorkItemAction(action="wait", version=item.version))
    assert item.status == "WAITING_REQUESTER"
    item, request = act(db, agent, item.id, WorkItemAction(action="resume", version=item.version))
    item, request = act(db, agent, item.id, WorkItemAction(action="resolve", version=item.version, note="Device replaced"))
    assert request.status == "resolved" and item.resolution_summary == "Device replaced"
    item, request = act(db, agent, item.id, WorkItemAction(action="close", version=item.version))
    assert item.status == "CLOSED" and request.status == "completed" and request.completed_at is not None


def test_unrelated_user_cannot_access_service_queue(db_session):
    db = db_session
    employee = _user(db, "employee@centralops.demo")
    try:
        list_work_items(db, employee, "team", None, 50, 0)
        assert False, "employee queue access should fail"
    except FulfillmentError as exc:
        assert exc.status_code == 403


def test_ordinary_team_approver_cannot_manage_fulfillment(db_session):
    db = db_session
    request = _approved_request(db)
    lead = _user(db, "service.lead@centralops.demo")
    approver = _user(db, "approver@centralops.demo")
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").first()
    item = ensure_work_item(db, request, {"owner_service_team_id": team.id}, lead)
    try:
        act(db, approver, item.id, WorkItemAction(action="assign", version=item.version))
        assert False, "APPROVER membership alone must not grant fulfillment actions"
    except FulfillmentError as exc:
        assert exc.status_code == 403


def test_stale_version_conflicts(db_session):
    db = db_session
    request = _approved_request(db)
    lead = _user(db, "service.lead@centralops.demo")
    agent = _user(db, "service.agent@centralops.demo")
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").first()
    item = ensure_work_item(db, request, {"owner_service_team_id": team.id}, lead)
    item, _ = act(db, agent, item.id, WorkItemAction(action="assign", version=1))
    try:
        act(db, agent, item.id, WorkItemAction(action="start", version=1))
        assert False, "stale version should conflict"
    except FulfillmentError as exc:
        assert exc.status_code == 409
