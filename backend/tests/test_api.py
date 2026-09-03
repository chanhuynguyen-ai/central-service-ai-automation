from conftest import login
from fastapi.testclient import TestClient


def test_health_reports_database(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_login_returns_user_and_token(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "employee@centralops.demo", "password": "Employee123!"},
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "employee"
    assert response.json()["access_token"]


def test_employee_submits_request_with_ai_triage(client: TestClient) -> None:
    response = client.post(
        "/api/v1/requests",
        headers=login(client),
        json={
            "title": "Urgent VPN access for a new analyst",
            "description": "The new analyst is blocked and needs finance system access before onboarding.",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["reference"].startswith("CSR-")
    assert body["status"] == "pending_approval"
    assert body["ai_category"] == "access_request"
    assert body["ai_priority"] == "urgent"
    assert body["ai_confidence"] >= 0.8


def test_employee_cannot_open_management_analytics(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/summary", headers=login(client))
    assert response.status_code == 403


def test_employee_cannot_read_another_employees_request(client: TestClient) -> None:
    approver_headers = login(client, "approver")
    request_id = client.get("/api/v1/requests", headers=approver_headers).json()["items"][0]["id"]
    response = client.get(
        f"/api/v1/requests/{request_id}",
        headers=login(client, "employee2"),
    )
    assert response.status_code == 404


def test_approver_can_approve_pending_request(client: TestClient) -> None:
    headers = login(client, "approver")
    requests = client.get("/api/v1/requests?status=pending_approval", headers=headers).json()[
        "items"
    ]
    request_id = requests[0]["id"]
    response = client.post(
        f"/api/v1/requests/{request_id}/decision",
        headers=headers,
        json={"decision": "approve", "comment": "Business owner confirmed."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_policy_assistant_returns_grounded_citation(client: TestClient) -> None:
    response = client.post(
        "/api/v1/assistant/chat",
        headers=login(client),
        json={"question": "When should I mark a request as urgent?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"]
    assert "Priority" in body["citations"][0]["title"]


def test_admin_reads_operational_metrics(client: TestClient) -> None:
    response = client.get("/api/v1/analytics/summary", headers=login(client, "admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["total_requests"] >= 5
    assert body["automation_success_rate"] == 100.0
    assert body["ai_triage_coverage"] == 100.0


def test_validation_rejects_incomplete_request(client: TestClient) -> None:
    response = client.post(
        "/api/v1/requests",
        headers=login(client),
        json={"title": "Help", "description": "Too short"},
    )
    assert response.status_code == 422


def test_power_platform_intake_runs_ai_triage(client: TestClient) -> None:
    response = client.post(
        "/api/v1/integrations/power-platform/intake",
        headers={"X-Integration-Key": "centralops-local-integration-key"},
        json={
            "requester_email": "employee@centralops.demo",
            "title": "VPN access for temporary finance analyst",
            "description": "The analyst is blocked and needs access before the reporting deadline.",
            "source_record_id": "SP-2048",
        },
    )
    assert response.status_code == 201
    assert response.json()["reference"].startswith("PA-SP-2048")
    assert response.json()["ai_category"] == "access_request"


def test_power_automate_records_human_decision(client: TestClient) -> None:
    headers = {"X-Integration-Key": "centralops-local-integration-key"}
    created = client.post(
        "/api/v1/integrations/power-platform/intake",
        headers=headers,
        json={
            "requester_email": "employee@centralops.demo",
            "title": "Purchase a replacement laptop charger",
            "description": "The employee needs a standard charger to continue working.",
        },
    ).json()
    response = client.post(
        f"/api/v1/integrations/power-platform/requests/{created['reference']}/decision",
        headers=headers,
        json={
            "approver_email": "approver@centralops.demo",
            "decision": "approve",
            "comment": "Standard equipment approved.",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
