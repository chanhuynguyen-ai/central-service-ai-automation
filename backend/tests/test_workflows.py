from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models.models import AuditEvent, ServiceRequest, User
from app.models.workflows import ApprovalDecision, ApprovalTask, WorkflowInstance
from tests.conftest import login

BASE = "/api/v1/workflows"
FORM = {"sections": [{"title": "Details", "fields": [
    {"key": "reason", "type": "text", "label": "Reason", "required": True},
]}]}


@contextmanager
def database(client):
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        yield db
    finally:
        generator.close()


def user_login(client, email, password="Manager123!"):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def setup_flow(client, *, steps=None, publish=True):
    admin = login(client, "admin")
    owner = login(client)
    manager = user_login(client, "manager.finance@centralops.demo")
    kind = client.post("/api/v1/catalog/request-types", headers=admin, json={"code": "M3_TEST", "category": "IT"}).json()
    version = client.post(f"/api/v1/catalog/request-types/{kind['id']}/versions", headers=admin, json={"title": "Test form", "form_schema": FORM}).json()
    assert client.post(f"/api/v1/catalog/request-types/{kind['id']}/versions/1/publish", headers=admin).status_code == 200
    definition = client.post(BASE + "/definitions", headers=admin, json={"code": "M3_FLOW", "name": "Test workflow", "request_type_id": kind["id"]}).json()
    with database(client) as db:
        approver_id = db.query(User).filter_by(email="approver@centralops.demo").one().id
    specs = steps if steps is not None else [
        {"name": "Manager review", "approver_resolver_type": "MANAGER"},
        {"name": "Service review", "approver_resolver_type": "USER", "approver_resolver_config": {"user_id": approver_id}},
    ]
    result = client.post(BASE + f"/definitions/{definition['id']}/versions", headers=admin, json={"steps": specs})
    assert result.status_code == 201, result.text
    if publish:
        assert client.post(BASE + f"/definitions/{definition['id']}/versions/1/publish", headers=admin).status_code == 200
    draft = client.post("/api/v1/requests/drafts", headers=owner, json={
        "request_type_version_id": version["id"], "title": "Replacement computer", "description": "My current computer is not working.", "form_data": {"reason": "hardware failure"},
    }).json()
    return admin, owner, manager, definition["id"], draft


def submit(client, owner, draft, revision=None):
    return client.post(BASE + f"/requests/{draft['id']}/submit", headers=owner,
                       json={"revision": revision or draft["revision"]})


def task_of(output, step=0, attempt=-1):
    return output["attempts"][attempt]["steps"][step]["tasks"][0]


def decide(client, headers, task, decision="approve", comment=""):
    return client.post(BASE + f"/approval-tasks/{task['id']}/decisions", headers=headers,
                       json={"version": task["version"], "decision": decision, "comment": comment})


def test_two_step_approval_is_sequential_and_not_fulfillment(client: TestClient):
    _, owner, manager, _, draft = setup_flow(client)
    first = submit(client, owner, draft)
    assert first.status_code == 200, first.text
    assert first.json()["status"] == "pending_approval"
    assert first.json()["attempts"][0]["steps"][1]["tasks"] == []
    assert client.get(BASE + "/approval-tasks", headers=manager).json()["total"] == 1
    result = decide(client, manager, task_of(first.json()))
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "pending_approval"
    second = task_of(result.json(), 1)
    final = decide(client, login(client, "approver"), second)
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "approved"
    assert final.json()["approval_state"] == "approved"
    assert final.json()["fulfillment_state"] == "not_queued"
    assert final.json()["approved_at"]
    assert client.get(BASE + "/approval-tasks", headers=manager).json()["total"] == 0


def test_duplicate_submission_and_decision_are_conflicts(client):
    _, owner, manager, _, draft = setup_flow(client)
    output = submit(client, owner, draft).json()
    assert submit(client, owner, draft).status_code == 409
    task = task_of(output)
    assert decide(client, manager, task).status_code == 200
    assert decide(client, manager, task).status_code == 409
    with database(client) as db:
        assert db.query(WorkflowInstance).count() == 1
        assert db.query(ApprovalDecision).count() == 1


def test_only_assigned_approver_can_decide_and_view(client):
    admin, owner, manager, _, draft = setup_flow(client)
    output = submit(client, owner, draft).json()
    task = task_of(output)
    unrelated = user_login(client, "manager.operations@centralops.demo")
    generic = login(client, "approver")
    for headers in [admin, owner, unrelated, generic]:
        assert decide(client, headers, task).status_code == 403
    assert client.get(BASE + f"/requests/{draft['id']}", headers=unrelated).status_code == 404
    assert client.get(BASE + f"/requests/{draft['id']}", headers=generic).status_code == 404
    assert client.get(BASE + f"/requests/{draft['id']}", headers=admin).status_code == 200
    assert client.get(BASE + f"/requests/{draft['id']}", headers=manager).status_code == 200
    assert client.get(BASE + "/requests", headers=generic).json()["total"] == 0


@pytest.mark.parametrize("problem", ["manager_missing", "manager_self", "inactive", "role_removed", "unpublished", "inactive_definition", "invalid_form"])
def test_submission_failure_rolls_back_everything(client, problem):
    admin, owner, _, definition, draft = setup_flow(client, publish=problem != "unpublished")
    with database(client) as db:
        employee = db.query(User).filter_by(email="employee@centralops.demo").one()
        manager = db.get(User, employee.manager_id)
        if problem == "manager_missing":
            employee.manager_id = None
        elif problem == "manager_self":
            employee.manager_id = employee.id
            employee.role = "approver"
        elif problem == "inactive":
            manager.is_active = False
        elif problem == "role_removed":
            manager.role_assignments.clear()
            manager.role = "employee"
        elif problem == "invalid_form":
            db.get(ServiceRequest, draft["id"]).form_data = {}
        db.commit()
    if problem == "inactive_definition":
        assert client.patch(BASE + f"/definitions/{definition}", headers=admin, json={"is_active": False}).status_code == 200
    response = submit(client, owner, draft)
    assert response.status_code == (422 if problem == "invalid_form" else 409), response.text
    with database(client) as db:
        record = db.get(ServiceRequest, draft["id"])
        assert record.status == "draft"
        assert record.submitted_at is None and record.due_at is None
        assert record.draft_revision == 1
        assert db.query(WorkflowInstance).count() == 0
        assert db.query(ApprovalTask).count() == 0
        assert db.query(AuditEvent).filter_by(event_type="request_submitted").count() == 0


def test_later_unavailable_approver_rolls_back_current_decision(client):
    _, owner, manager, _, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    task = task_of(out)
    with database(client) as db:
        db.query(User).filter_by(email="approver@centralops.demo").one().is_active = False
        db.commit()
    assert decide(client, manager, task).status_code == 409
    with database(client) as db:
        assert db.get(ApprovalTask, task["id"]).status == "PENDING"
        assert db.query(ApprovalDecision).count() == 0


def test_rejection_is_terminal(client):
    _, owner, manager, _, draft = setup_flow(client)
    output = submit(client, owner, draft).json()
    result = decide(client, manager, task_of(output), "reject", "No business justification.")
    assert result.status_code == 200
    assert result.json()["status"] == "rejected"
    assert result.json()["attempts"][0]["steps"][1]["status"] == "CANCELLED"
    assert submit(client, owner, draft, result.json()["revision"]).status_code == 409
    assert client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=owner).status_code == 404


def test_request_changes_restart_preserves_history_and_private_edits(client):
    _, owner, manager, _, draft = setup_flow(client)
    output = submit(client, owner, draft).json()
    task = task_of(output)
    changed = decide(client, manager, task, "request_changes", "Explain the business impact.")
    assert changed.status_code == 200
    assert changed.json()["status"] == "changes_requested"
    editable = client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=owner).json()
    assert editable["status"] == "changes_requested"
    update = client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=owner, json={
        "revision": editable["revision"], "title": "Edited private title", "description": "New customer-facing business context.", "form_data": {"reason": "private unsent draft"},
    })
    assert update.status_code == 200, update.text
    previous = client.get(BASE + f"/requests/{draft['id']}", headers=manager).json()
    assert previous["title"] == draft["title"]
    assert previous["attempts"][0]["snapshot"]["form_data"] == {"reason": "hardware failure"}
    resubmit = submit(client, owner, draft, update.json()["revision"])
    assert resubmit.status_code == 200, resubmit.text
    assert resubmit.json()["attempt"] == 2
    assert resubmit.json()["attempts"][0]["steps"][0]["tasks"][0]["decision"]["comment"] == "Explain the business impact."
    assert resubmit.json()["attempts"][1]["snapshot"]["form_data"]["reason"] == "private unsent draft"
    assert resubmit.json()["attempts"][1]["steps"][0]["status"] == "ACTIVE"
    assert decide(client, manager, task).status_code == 409


def test_workflow_version_snapshot_survives_publication(client):
    admin, owner, manager, definition, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    version = client.post(BASE + f"/definitions/{definition}/versions", headers=admin, json={"steps": [{"name": "New manager only", "approver_resolver_type": "MANAGER"}]})
    assert version.status_code == 201
    assert client.post(BASE + f"/definitions/{definition}/versions/2/publish", headers=admin).status_code == 200
    invalid = client.put(BASE + f"/definitions/{definition}/versions/1", headers=admin, json={"steps": [{"name": "Rewrite history", "approver_resolver_type": "MANAGER"}]})
    assert invalid.status_code == 409
    next_out = decide(client, manager, task_of(out)).json()
    assert next_out["status"] == "pending_approval"
    assert len(next_out["attempts"][0]["snapshot"]["workflow"]["steps"]) == 2


@pytest.mark.parametrize("resolver", ["ROLE", "TEAM_LEAD"])
def test_resolvers_use_department_or_service_lead(client, resolver):
    from app.models.models import ServiceTeam
    with database(client) as db:
        team_id = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE").one().id
    config = {"role_code": "MANAGER"} if resolver == "ROLE" else {"service_team_id": team_id}
    _, owner, _, _, draft = setup_flow(client, steps=[{"name": "Scoped approval", "approver_resolver_type": resolver, "approver_resolver_config": config}])
    out = submit(client, owner, draft)
    assert out.status_code == 200, out.text
    task = task_of(out.json())
    expected = "Finance Manager" if resolver == "ROLE" else "Central Service Lead"
    assert task["approver_name"] == expected


def test_all_mode_requires_each_assigned_approver(client):
    with database(client) as db:
        manager = db.query(User).filter_by(email="manager.finance@centralops.demo").one()
        other = db.query(User).filter_by(email="manager.operations@centralops.demo").one()
        other.department_id = manager.department_id
        db.commit()
    _, owner, manager, _, draft = setup_flow(client, steps=[{"name": "Department approval", "approver_resolver_type": "ROLE", "approver_resolver_config": {"role_code": "MANAGER"}}])
    out = submit(client, owner, draft).json()
    tasks = out["attempts"][0]["steps"][0]["tasks"]
    assert len(tasks) == 2
    first = decide(client, manager, tasks[0])
    assert first.status_code == 200
    assert first.json()["status"] == "pending_approval"
    other = user_login(client, "manager.operations@centralops.demo")
    result = decide(client, other, tasks[1])
    assert result.status_code == 200
    assert result.json()["status"] == "approved"


def test_structured_workflow_cannot_be_bypassed_by_legacy_api(client):
    admin, owner, manager, _, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    for headers in [owner, admin, manager]:
        assert client.get(f"/api/v1/requests/{draft['id']}", headers=headers).status_code == 404
        assert client.post(f"/api/v1/requests/{draft['id']}/decision", headers=headers, json={"decision": "approve"}).status_code in {403, 404}
        assert client.patch(f"/api/v1/requests/{draft['id']}/status", headers=headers, json={"status": "completed"}).status_code in {403, 404}
    integration = {"X-Integration-Key": "centralops-local-integration-key"}
    assert client.post(f"/api/v1/integrations/power-platform/requests/{out['reference']}/decision", headers=integration, json={"approver_email": "admin@centralops.demo", "decision": "approve"}).status_code == 404
    assert client.post("/api/v1/assistant/chat", headers=admin, json={"question": "Explain request status", "request_reference": out["reference"]}).status_code == 404


def test_strict_configuration_and_mutation_permissions(client):
    admin, owner, _, definition, draft = setup_flow(client)
    assert client.get(BASE + "/definitions").status_code == 401
    assert client.get(BASE + "/definitions", headers=owner).status_code == 403
    assert client.post(BASE + f"/definitions/{definition}/versions", headers=owner, json={"steps": [{"name": "Manager", "approver_resolver_type": "MANAGER"}]}).status_code == 403
    for step in [
        {"name": "Bad config", "approver_resolver_type": "MANAGER", "approver_resolver_config": {"user_id": 1}},
        {"name": "Unsupported", "approver_resolver_type": "MANAGER", "approval_mode": "ANY"},
        {"name": "Unsupported", "approver_resolver_type": "MANAGER", "condition_rule": {"amount": 1}},
    ]:
        assert client.post(BASE + f"/definitions/{definition}/versions", headers=admin, json={"steps": [step]}).status_code == 422
    assert client.post(BASE + f"/requests/{draft['id']}/submit", headers=owner, json={"revision": 1, "approver_id": 1}).status_code == 422


def test_seed_workflows_is_repeatable(client):
    from app.db.seed_catalog import seed_catalog
    from app.db.seed_workflows import seed_workflows
    with database(client) as db:
        seed_catalog(db)
        assert seed_workflows(db) == 3
        assert seed_workflows(db) == 0


def test_auditor_read_only_and_deactivated_assignee_rejected(client):
    _, owner, manager, _, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    auditor = user_login(client, "auditor@centralops.demo", "Auditor123!")
    assert client.get(BASE + f"/requests/{draft['id']}", headers=auditor).status_code == 200
    assert decide(client, auditor, task_of(out)).status_code == 403
    with database(client) as db:
        db.query(User).filter_by(email="manager.finance@centralops.demo").one().is_active = False
        db.commit()
    assert decide(client, manager, task_of(out)).status_code == 401


def test_direct_self_assigned_task_still_cannot_be_approved(client):
    _, owner, _, _, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    task = task_of(out)
    with database(client) as db:
        employee = db.query(User).filter_by(email="employee@centralops.demo").one()
        employee.role = "approver"
        db.get(ApprovalTask, task["id"]).approver_user_id = employee.id
        db.commit()
    response = decide(client, owner, task)
    assert response.status_code == 403
    assert "Self approval" in response.json()["detail"]
    with database(client) as db:
        assert db.query(ApprovalDecision).count() == 0
