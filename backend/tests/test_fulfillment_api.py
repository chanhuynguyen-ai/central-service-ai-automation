from app.models.fulfillment import ServiceWorkItem
from app.models.models import ServiceRequest, ServiceTeam, User
from app.services.fulfillment import ensure_work_item
from tests.conftest import login

BASE = "/api/v1/fulfillment"


def user_login(client, email, password):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def queued_item(db):
    requester = db.query(User).filter_by(email="employee@centralops.demo").one()
    lead = db.query(User).filter_by(email="service.lead@centralops.demo").one()
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").one()
    request = ServiceRequest(
        reference="FUL-API-1",
        title="API fulfillment test",
        description="Approved request for service API tests.",
        category="IT",
        priority="medium",
        status="approved",
        department=requester.department,
        requester_id=requester.id,
        approval_state="approved",
        fulfillment_state="not_queued",
        workflow_attempt=1,
    )
    db.add(request)
    db.flush()
    item = ensure_work_item(db, request, {"owner_service_team_id": team.id}, lead)
    db.commit()
    return item.id


def test_service_queue_is_server_side_restricted(client):
    employee = login(client)
    approver = login(client, "approver")
    agent = user_login(client, "service.agent@centralops.demo", "ServiceAgent123!")
    lead = user_login(client, "service.lead@centralops.demo", "ServiceLead123!")
    admin = login(client, "admin")

    assert client.get(BASE + "/work-items", headers=employee).status_code == 403
    assert client.get(BASE + "/work-items", headers=approver).status_code == 403
    assert client.get(BASE + "/work-items", headers=agent).status_code == 200
    assert client.get(BASE + "/work-items", headers=lead).status_code == 200
    assert client.get(BASE + "/work-items", headers=admin).status_code == 200


def test_agent_can_claim_only_with_current_version(client, db_session):
    item_id = queued_item(db_session)
    agent = user_login(client, "service.agent@centralops.demo", "ServiceAgent123!")

    queue = client.get(BASE + "/work-items?scope=unassigned", headers=agent)
    assert queue.status_code == 200
    row = next(item for item in queue.json()["items"] if item["id"] == item_id)
    response = client.post(
        BASE + f"/work-items/{item_id}/actions",
        headers=agent,
        json={"action": "assign", "version": row["version"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ASSIGNED"
    assert response.json()["assignee_name"] == "Central Service Agent"

    stale = client.post(
        BASE + f"/work-items/{item_id}/actions",
        headers=agent,
        json={"action": "start", "version": row["version"]},
    )
    assert stale.status_code == 409


def test_team_lead_can_assign_eligible_agent_but_employee_cannot_act(client, db_session):
    item_id = queued_item(db_session)
    lead = user_login(client, "service.lead@centralops.demo", "ServiceLead123!")
    employee = login(client)
    agent = db_session.query(User).filter_by(email="service.agent@centralops.demo").one()

    denied = client.post(
        BASE + f"/work-items/{item_id}/actions",
        headers=employee,
        json={"action": "assign", "version": 1},
    )
    assert denied.status_code == 403

    assigned = client.post(
        BASE + f"/work-items/{item_id}/actions",
        headers=lead,
        json={"action": "assign", "version": 1, "assignee_user_id": agent.id},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["assignee_user_id"] == agent.id

    db_session.expire_all()
    assert db_session.get(ServiceWorkItem, item_id).assignee_user_id == agent.id
