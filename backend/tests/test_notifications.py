from datetime import UTC, datetime

from app.models.models import User
from app.models.notifications import Notification
from app.services.notifications import enqueue_pair, mark_email_failed
from tests.conftest import login
from tests.test_workflows import decide, setup_flow, submit, task_of


def test_notification_pair_is_idempotent_and_api_is_recipient_scoped(client, db_session):
    recipient = db_session.query(User).filter_by(email="employee@centralops.demo").one()
    other = db_session.query(User).filter_by(email="other.employee@centralops.demo").one()
    first = enqueue_pair(
        db_session,
        recipient=recipient,
        event_key="test:event:1",
        kind="TEST",
        subject="Test notification",
        body="Safe test body",
    )
    second = enqueue_pair(
        db_session,
        recipient=recipient,
        event_key="test:event:1",
        kind="TEST",
        subject="Ignored duplicate",
        body="Ignored duplicate body",
    )
    db_session.commit()
    assert [row.id for row in first] == [row.id for row in second]
    assert db_session.query(Notification).filter_by(event_key="test:event:1").count() == 2

    owner_headers = login(client, "employee")
    other_headers = login(client, "employee2")
    page = client.get("/api/v1/notifications", headers=owner_headers)
    assert page.status_code == 200
    assert page.json()["unread"] == 1
    notification_id = page.json()["items"][0]["id"]

    assert client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=other_headers,
    ).status_code == 404
    read = client.post(
        f"/api/v1/notifications/{notification_id}/read",
        headers=owner_headers,
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None
    assert client.get("/api/v1/notifications", headers=owner_headers).json()["unread"] == 0
    assert db_session.get(User, other.id) is not None


def test_email_failure_backoff_ends_in_dead_state(db_session):
    recipient = db_session.query(User).filter_by(email="employee@centralops.demo").one()
    row = enqueue_pair(
        db_session,
        recipient=recipient,
        event_key="test:email:retry",
        kind="TEST",
        subject="Retry me",
        body="Retry body",
    )[1]
    before = datetime.now(UTC)
    mark_email_failed(
        db_session,
        row,
        error="smtp unavailable",
        retry_seconds=5,
        max_attempts=2,
    )
    assert row.status == "FAILED"
    assert row.attempts == 1
    assert row.available_at >= before
    mark_email_failed(
        db_session,
        row,
        error="smtp unavailable again",
        retry_seconds=5,
        max_attempts=2,
    )
    assert row.status == "DEAD"
    assert row.attempts == 2


def test_workflow_lifecycle_creates_assignment_and_requester_notifications(client):
    _, owner, manager, _, draft = setup_flow(client)
    submitted = submit(client, owner, draft)
    assert submitted.status_code == 200, submitted.text

    manager_feed = client.get("/api/v1/notifications", headers=manager).json()
    assert any(row["kind"] == "APPROVAL_ASSIGNED" for row in manager_feed["items"])

    first = decide(client, manager, task_of(submitted.json()), "approve")
    assert first.status_code == 200, first.text
    approver = login(client, "approver")
    approver_feed = client.get("/api/v1/notifications", headers=approver).json()
    assert any(row["kind"] == "APPROVAL_ASSIGNED" for row in approver_feed["items"])

    final = decide(client, approver, task_of(first.json(), 1), "approve")
    assert final.status_code == 200, final.text
    owner_feed = client.get("/api/v1/notifications", headers=owner).json()
    assert any(row["kind"] == "REQUEST_APPROVED" for row in owner_feed["items"])


def test_request_changes_notifies_requester(client):
    _, owner, manager, _, draft = setup_flow(client)
    submitted = submit(client, owner, draft).json()
    changed = decide(client, manager, task_of(submitted), "request_changes", "Add details")
    assert changed.status_code == 200, changed.text
    feed = client.get("/api/v1/notifications", headers=owner).json()
    assert any(row["kind"] == "CHANGES_REQUESTED" for row in feed["items"])
