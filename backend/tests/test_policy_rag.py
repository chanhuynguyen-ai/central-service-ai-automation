from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from tests.conftest import login


def _create_policy(client: TestClient, headers: dict[str, str], **overrides) -> dict:
    payload = {
        "slug": "laptop-replacement-policy",
        "title": "Laptop Replacement Policy",
        "version": "1.0",
        "source_name": "laptop-policy.md",
        "access_scope": "ALL",
        "content": (
            "# Eligibility\n\nEmployees may request a replacement laptop when repeated hardware failures "
            "materially interrupt client or business work.\n\n# Required information\n\nInclude the "
            "business impact, managed platform, cost center, and required date."
        ),
    }
    payload.update(overrides)
    response = client.post("/api/v1/ai/knowledge/documents", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_policy_ingestion_requires_admin_and_returns_grounded_citation(client: TestClient) -> None:
    admin = login(client, "admin")
    employee = login(client, "employee")
    forbidden = client.post(
        "/api/v1/ai/knowledge/documents",
        headers=employee,
        json={
            "slug": "employee-write",
            "title": "Employee write attempt",
            "version": "1",
            "content": "This content is intentionally long enough to pass request validation.",
        },
    )
    assert forbidden.status_code == 403

    document = _create_policy(client, admin)
    assert document["chunk_count"] >= 1
    answer = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=employee,
        json={"question": "When may I request a replacement laptop?"},
    )
    assert answer.status_code == 200
    body = answer.json()
    assert body["grounded"] is True
    assert body["insufficient_evidence"] is False
    assert body["citations"]
    assert body["citations"][0]["title"] == "Laptop Replacement Policy"


def test_department_scope_is_filtered_before_retrieval(client: TestClient) -> None:
    admin = login(client, "admin")
    employee = login(client, "employee")
    other = login(client, "employee2")
    employee_user = client.get("/api/v1/auth/me", headers=employee).json()
    lookups = client.get("/api/v1/requests/drafts/lookups", headers=employee).json()
    department = next(item for item in lookups["departments"] if item["name"] == employee_user["department"])

    _create_policy(
        client,
        admin,
        slug="finance-private-policy",
        title="Finance Private Reimbursement Policy",
        access_scope="DEPARTMENT",
        department_id=department["id"],
        content=(
            "# Finance-only rule\n\nThe confidential finance reimbursement codeword is ORCHID-742. "
            "Only the scoped department should retrieve this evidence."
        ),
    )

    allowed = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=employee,
        json={"question": "What is the confidential finance reimbursement codeword?"},
    ).json()
    assert allowed["grounded"] is True
    assert any(item["title"] == "Finance Private Reimbursement Policy" for item in allowed["citations"])

    denied = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=other,
        json={"question": "What is the confidential finance reimbursement codeword?"},
    ).json()
    assert all(item["title"] != "Finance Private Reimbursement Policy" for item in denied["citations"])
    assert "ORCHID-742" not in denied["answer"]


def test_role_scope_and_effective_dates_are_enforced(client: TestClient) -> None:
    admin = login(client, "admin")
    employee = login(client, "employee")
    auditor = login(client, "auditor")
    _create_policy(
        client,
        admin,
        slug="audit-private-policy",
        title="Audit Private Control Policy",
        access_scope="ROLE",
        role_code="AUDITOR",
        content=(
            "# Restricted control\n\nThe audit-only control phrase is VIOLET-931 and is restricted "
            "to authorized auditors."
        ),
    )
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    _create_policy(
        client,
        admin,
        slug="future-policy",
        title="Future Device Policy",
        effective_from=future,
        content=(
            "# Future rule\n\nThe future-only laptop phrase is FUTURE-DEVICE-991 and must not be "
            "retrieved before its effective date."
        ),
    )

    employee_answer = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=employee,
        json={"question": "What is VIOLET-931?"},
    ).json()
    assert "VIOLET-931" not in employee_answer["answer"]
    assert all(item["title"] != "Audit Private Control Policy" for item in employee_answer["citations"])

    auditor_answer = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=auditor,
        json={"question": "What is the audit-only control phrase VIOLET-931?"},
    ).json()
    assert auditor_answer["grounded"] is True
    assert any(item["title"] == "Audit Private Control Policy" for item in auditor_answer["citations"])

    future_answer = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=employee,
        json={"question": "What does FUTURE-DEVICE-991 mean?"},
    ).json()
    assert "FUTURE-DEVICE-991" not in future_answer["answer"]
    assert all(item["title"] != "Future Device Policy" for item in future_answer["citations"])


def test_insufficient_evidence_is_explicit_and_has_no_citations(client: TestClient) -> None:
    employee = login(client, "employee")
    response = client.post(
        "/api/v1/ai/knowledge/ask",
        headers=employee,
        json={"question": "What is the interplanetary teleportation reimbursement rule?"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
