from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_request(
    client: TestClient,
    headers: dict[str, str],
    title: str,
) -> dict:
    response = client.post(
        "/api/v1/requests",
        headers=headers,
        json={
            "title": title,
            "description": (
                "This request contains enough detail to exercise centralized "
                "authorization behavior in the API."
            ),
        },
    )
    assert response.status_code == 201
    return response.json()


def test_employee_only_lists_own_requests(client: TestClient) -> None:
    employee = _login(client, "employee@centralops.demo", "Employee123!")
    other_employee = _login(
        client,
        "other.employee@centralops.demo",
        "Employee123!",
    )

    own = _create_request(client, employee, "Finance employee visibility request")
    other = _create_request(client, other_employee, "Operations employee visibility request")

    response = client.get("/api/v1/requests", headers=employee)

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert own["id"] in ids
    assert other["id"] not in ids


def test_manager_lists_own_and_direct_report_requests_only(client: TestClient) -> None:
    finance_employee = _login(client, "employee@centralops.demo", "Employee123!")
    operations_employee = _login(
        client,
        "other.employee@centralops.demo",
        "Employee123!",
    )
    finance_manager = _login(
        client,
        "manager.finance@centralops.demo",
        "Manager123!",
    )

    finance_request = _create_request(
        client,
        finance_employee,
        "Finance direct report request",
    )
    operations_request = _create_request(
        client,
        operations_employee,
        "Operations employee request",
    )
    manager_request = _create_request(
        client,
        finance_manager,
        "Manager own request",
    )

    response = client.get("/api/v1/requests", headers=finance_manager)

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert finance_request["id"] in ids
    assert manager_request["id"] in ids
    assert operations_request["id"] not in ids


def test_normalized_approver_assignment_allows_manager_to_approve(client: TestClient) -> None:
    employee = _login(client, "employee@centralops.demo", "Employee123!")
    manager = _login(
        client,
        "manager.finance@centralops.demo",
        "Manager123!",
    )
    request = _create_request(
        client,
        employee,
        "Manager approval through normalized role assignment",
    )

    response = client.post(
        f"/api/v1/requests/{request['id']}/decision",
        headers=manager,
        json={"decision": "approve", "comment": "Approved by direct manager."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_manager_cannot_approve_own_request(client: TestClient) -> None:
    manager = _login(
        client,
        "manager.finance@centralops.demo",
        "Manager123!",
    )
    request = _create_request(
        client,
        manager,
        "Manager self approval must remain forbidden",
    )

    response = client.post(
        f"/api/v1/requests/{request['id']}/decision",
        headers=manager,
        json={"decision": "approve", "comment": "Must be rejected."},
    )

    assert response.status_code == 403


def test_auditor_can_read_but_cannot_mutate(client: TestClient) -> None:
    employee = _login(client, "employee@centralops.demo", "Employee123!")
    auditor = _login(client, "auditor@centralops.demo", "Auditor123!")
    request = _create_request(
        client,
        employee,
        "Auditor read only request",
    )

    detail = client.get(
        f"/api/v1/requests/{request['id']}",
        headers=auditor,
    )
    decision = client.post(
        f"/api/v1/requests/{request['id']}/decision",
        headers=auditor,
        json={"decision": "approve", "comment": "Auditor must not approve."},
    )
    status_change = client.patch(
        f"/api/v1/requests/{request['id']}/status",
        headers=auditor,
        json={"status": "in_progress", "comment": "Auditor must not mutate."},
    )

    assert detail.status_code == 200
    assert decision.status_code == 403
    assert status_change.status_code == 403


def test_admin_can_view_and_decide_request(client: TestClient) -> None:
    employee = _login(client, "employee@centralops.demo", "Employee123!")
    admin = _login(client, "admin@centralops.demo", "Admin123!")
    request = _create_request(
        client,
        employee,
        "Admin permission request",
    )

    detail = client.get(
        f"/api/v1/requests/{request['id']}",
        headers=admin,
    )
    decision = client.post(
        f"/api/v1/requests/{request['id']}/decision",
        headers=admin,
        json={"decision": "approve", "comment": "Admin override for prototype."},
    )

    assert detail.status_code == 200
    assert decision.status_code == 200
