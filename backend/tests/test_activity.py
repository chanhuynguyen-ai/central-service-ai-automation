from uuid import uuid4

import pytest
from sqlalchemy import event

from app.models.activity import RequestComment, RequestEvent
from app.models.models import AuditEvent, Role, User, UserRole
from app.services.audit import safe_details
from tests.conftest import login
from tests.test_workflows import database, decide, setup_flow, submit, task_of, user_login


def endpoint(draft, suffix):
    return f"/api/v1/activity/requests/{draft['id']}/{suffix}"


def post(client, draft, headers, body="Shared business update", visibility="REQUESTER_VISIBLE", key=None):
    return client.post(endpoint(draft, "comments"), headers=headers, json={
        "body": body, "visibility": visibility, "client_token": key or str(uuid4()),
    })


def test_public_comment_and_ordered_submission_timeline(client):
    _, owner, _, _, draft = setup_flow(client)
    assert client.get(endpoint(draft, "timeline"), headers=owner).status_code == 404
    assert post(client, draft, owner).status_code == 404
    assert submit(client, owner, draft).status_code == 200
    timeline = client.get(endpoint(draft, "timeline"), headers=owner).json()
    assert [row["event_type"] for row in reversed(timeline["items"])] == [
        "REQUEST_SUBMITTED", "WORKFLOW_STARTED", "APPROVAL_ASSIGNED",
    ]
    response = post(client, draft, owner)
    assert response.status_code == 201, response.text
    assert response.json()["author_name"] == "Employee Demo"
    assert client.get(endpoint(draft, "comments"), headers=owner).json()["items"][0]["body"] == "Shared business update"
    data = client.get(endpoint(draft, "timeline"), headers=owner).json()
    assert data["items"][0]["event_type"] == "COMMENT_ADDED"
    assert "Shared business update" not in str(data)


def test_internal_note_hidden_in_body_timeline_and_pagination(client):
    admin, owner, manager, _, draft = setup_flow(client)
    submit(client, owner, draft)
    assert post(client, draft, manager, "CONFIDENTIAL_M4", "INTERNAL").status_code == 201
    assert client.get(endpoint(draft, "comments") + "?visibility=INTERNAL", headers=owner).status_code == 403
    assert "CONFIDENTIAL_M4" not in client.get(endpoint(draft, "comments"), headers=owner).text
    assert "INTERNAL_NOTE_ADDED" not in client.get(endpoint(draft, "timeline"), headers=owner).text
    page = client.get(endpoint(draft, "timeline") + "?limit=3", headers=owner).json()
    assert len(page["items"]) == 3 and page["next_before_id"] is None
    assert "CONFIDENTIAL_M4" in client.get(endpoint(draft, "comments") + "?visibility=INTERNAL", headers=manager).text
    # Auditors may read internal notes but may not add either type of comment.
    auditor = user_login(client, "auditor@centralops.demo", "Auditor123!")
    assert "CONFIDENTIAL_M4" in client.get(endpoint(draft, "comments") + "?visibility=INTERNAL", headers=auditor).text
    assert post(client, draft, auditor).status_code == 403
    assert post(client, draft, auditor, visibility="INTERNAL").status_code == 403
    assert post(client, draft, owner, visibility="INTERNAL").status_code == 403
    assert "CONFIDENTIAL_M4" not in client.get("/api/v1/audit/events", headers=admin).text


def test_internal_requester_exclusion_even_with_admin_role(client):
    _, owner, manager, _, draft = setup_flow(client)
    submit(client, owner, draft)
    post(client, draft, manager, "NOT_FOR_REQUESTER", "INTERNAL")
    with database(client) as db:
        user = db.query(User).filter_by(email="employee@centralops.demo").one()
        user.role = "admin"
        db.commit()
    access = client.get(endpoint(draft, "permissions"), headers=owner).json()
    assert access == {"can_comment": True, "can_read_internal": False, "can_write_internal": False}
    assert client.get(endpoint(draft, "comments") + "?visibility=INTERNAL", headers=owner).status_code == 403
    assert "INTERNAL_NOTE_ADDED" not in client.get(endpoint(draft, "timeline"), headers=owner).text


def test_wrong_account_and_unassigned_approver_cannot_read_or_post(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    for headers in (login(client, "employee2"), login(client, "approver")):
        for suffix in ("permissions", "timeline", "comments"):
            assert client.get(endpoint(draft, suffix), headers=headers).status_code == 404
        assert post(client, draft, headers).status_code == 404
    assert client.get(endpoint(draft, "timeline")).status_code == 401


def test_idempotent_comment_retry_and_conflicting_key(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    key = str(uuid4())
    first = post(client, draft, owner, key=key)
    second = post(client, draft, owner, key=key)
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert post(client, draft, owner, body="Changed body", key=key).status_code == 409
    with database(client) as db:
        assert db.query(RequestComment).count() == 1
        assert db.query(RequestEvent).filter_by(event_type="COMMENT_ADDED").count() == 1
        assert db.query(AuditEvent).filter_by(event_type="request_comment_added").count() == 1


def test_strict_payload_and_no_history_mutation_endpoints(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    for extra in ({"author_user_id": 1}, {"visibility": "PUBLIC"}, {"created_at": "2020-01-01"}):
        payload = {"body": "Safe body", "client_token": str(uuid4()), **extra}
        assert client.post(endpoint(draft, "comments"), headers=owner, json=payload).status_code == 422
    for body in ("   ", "x" * 5001, "invalid\x00value"):
        assert post(client, draft, owner, body=body).status_code == 422
    for verb in (client.put, client.delete):
        assert verb(endpoint(draft, "comments"), headers=owner).status_code == 405
    assert post(client, draft, owner, body="<script>alert(1)</script> Plain text").status_code == 201


def test_cursor_paging_does_not_repeat_rows(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    for body in ("first", "second", "third"):
        post(client, draft, owner, body=body)
    page = client.get(endpoint(draft, "comments") + "?limit=2", headers=owner).json()
    assert [r["body"] for r in page["items"]] == ["third", "second"]
    older = client.get(endpoint(draft, "comments") + f"?limit=2&before_id={page['next_before_id']}", headers=owner).json()
    assert [r["body"] for r in older["items"]] == ["first"]
    assert older["next_before_id"] is None
    assert client.get(endpoint(draft, "timeline") + "?limit=1000", headers=owner).status_code == 422


def test_comment_audit_failure_rolls_back_comment_and_event(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    def fail(_mapper, _connection, target):
        if target.event_type == "COMMENT_ADDED":
            raise RuntimeError("injected event failure")
    event.listen(RequestEvent, "before_insert", fail)
    try:
        with pytest.raises(RuntimeError, match="injected event failure"):
            post(client, draft, owner)
    finally:
        event.remove(RequestEvent, "before_insert", fail)
    with database(client) as db:
        assert db.query(RequestComment).count() == 0
        assert db.query(AuditEvent).filter_by(event_type="request_comment_added").count() == 0


def test_decision_events_atomic_no_private_revision_values(client):
    _, owner, manager, _, draft = setup_flow(client)
    out = submit(client, owner, draft).json()
    response = decide(client, manager, task_of(out), "request_changes", "Explain the cost center")
    assert response.status_code == 200
    data = client.get(endpoint(draft, "timeline"), headers=owner).json()
    assert data["items"][0]["event_type"] == "CHANGES_REQUESTED"
    assert "Explain the cost center" not in str(data)  # decision body lives in authorized snapshots
    editable = client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=owner).json()
    client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=owner, json={
        "revision": editable["revision"], "title": "Private unsent title",
        "description": "Private unsent context for an employee", "form_data": {"reason": "PRIVATE_DRAFT"},
    })
    assert "PRIVATE_DRAFT" not in client.get(endpoint(draft, "timeline"), headers=manager).text
    assert decide(client, manager, task_of(out)).status_code == 409
    with database(client) as db:
        assert db.query(RequestEvent).filter_by(event_type="CHANGES_REQUESTED").count() == 1


def test_audit_api_restricts_and_redacts_historical_payloads(client):
    admin, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    with database(client) as db:
        db.add(AuditEvent(event_type="legacy_event", request_id=draft["id"], details={
            "password": "SECRET_PASSWORD", "comment": "SECRET_COMMENT", "token": "SECRET_TOKEN",
            "form_data": {"medical": "PRIVATE"}, "decision": {"bad": "data"}, "attempt": 1,
        }))
        db.commit()
    assert client.get("/api/v1/audit/events", headers=owner).status_code == 403
    assert client.get("/api/v1/audit/events").status_code == 401
    page = client.get("/api/v1/audit/events?event_type=legacy_event", headers=admin).json()
    assert page["items"][0]["details"] == {"attempt": 1}
    assert "SECRET" not in str(page) and "PRIVATE" not in str(page)
    with database(client) as db:
        assert db.query(AuditEvent).filter_by(event_type="audit_log_viewed").count() >= 1


def test_auth_audit_no_credentials_and_context_uuid(client):
    request_id = str(uuid4())
    response = client.post("/api/v1/auth/login", headers={"X-Request-ID": request_id}, json={
        "email": "employee@centralops.demo", "password": "Employee123!",
    })
    assert response.status_code == 200
    first = response.json()
    refresh = client.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert refresh.status_code == 200
    assert client.post("/api/v1/auth/logout", json={"refresh_token": refresh.json()["refresh_token"]}).status_code == 204
    assert client.post("/api/v1/auth/login", json={"email": "employee@centralops.demo", "password": "WRONGPASSWORD"}).status_code == 401
    with database(client) as db:
        rows = db.query(AuditEvent).filter(AuditEvent.event_type.like("auth_%")).all()
        assert {r.event_type for r in rows} >= {"auth_login", "auth_refresh", "auth_logout", "auth_login_failed"}
        assert next(r for r in rows if r.event_type == "auth_login").correlation_id == request_id
        assert first["refresh_token"] not in str([r.details for r in rows])
        assert all(r.details == {} for r in rows)


def test_orm_history_is_append_only_and_role_changes_recorded(client):
    with database(client) as db:
        row = db.query(AuditEvent).first()
        row.event_type = "tampered"
        with pytest.raises(ValueError, match="append-only"):
            db.flush()
        db.rollback()
        user = db.query(User).filter_by(email="other.employee@centralops.demo").one()
        role = db.query(Role).filter_by(code="AUDITOR").one()
        admin = db.query(User).filter_by(email="admin@centralops.demo").one()
        db.info["audit_actor_id"] = admin.id
        assignment = UserRole(user_id=user.id, role_id=role.id)
        db.add(assignment)
        db.flush()
        db.delete(assignment)
        db.commit()
        rows = db.query(AuditEvent).filter(AuditEvent.event_type.in_(["role_assigned", "role_removed"]), AuditEvent.actor_id == admin.id).all()
        assert {r.event_type for r in rows} == {"role_assigned", "role_removed"}
        assert all(r.details == {"user_id": user.id, "role_id": role.id} for r in rows)


def test_safe_details_is_strict():
    assert safe_details({"attempt": True, "session_id": "secret", "decision": [], "password": "secret"}) == {}
    assert safe_details("invalid legacy metadata") == {}
