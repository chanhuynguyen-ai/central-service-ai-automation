from fastapi.testclient import TestClient

from tests.conftest import login


def _version_payload(title: str = "Laptop Request") -> dict:
    return {
        "title": title,
        "description": "Request a managed laptop for business use.",
        "form_schema": {
            "sections": [
                {
                    "title": "Request details",
                    "fields": [
                        {
                            "key": "reason",
                            "type": "textarea",
                            "label": "Reason",
                            "required": True,
                        },
                        {
                            "key": "urgency",
                            "type": "select",
                            "label": "Urgency",
                            "required": True,
                            "options": [
                                {"value": "normal", "label": "Normal"},
                                {"value": "high", "label": "High"},
                            ],
                        },
                    ],
                }
            ]
        },
    }


def _create_type(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/api/v1/catalog/request-types",
        headers=headers,
        json={
            "code": "IT_LAPTOP",
            "category": "IT",
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_employee_sees_only_published_catalog_entries(client: TestClient) -> None:
    admin_headers = login(client, "admin")
    employee_headers = login(client, "employee")
    request_type = _create_type(client, admin_headers)

    version = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=_version_payload(),
    )
    assert version.status_code == 201

    before_publish = client.get(
        "/api/v1/catalog/request-types",
        headers=employee_headers,
    )
    assert before_publish.status_code == 200
    assert before_publish.json() == []

    published = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1/publish",
        headers=admin_headers,
    )
    assert published.status_code == 200
    assert published.json()["status"] == "PUBLISHED"

    catalog = client.get(
        "/api/v1/catalog/request-types",
        headers=employee_headers,
    )
    assert catalog.status_code == 200
    assert len(catalog.json()) == 1
    assert catalog.json()[0]["code"] == "IT_LAPTOP"
    assert catalog.json()[0]["published_version"]["version"] == 1


def test_employee_cannot_mutate_request_catalog(client: TestClient) -> None:
    employee_headers = login(client, "employee")

    response = client.post(
        "/api/v1/catalog/request-types",
        headers=employee_headers,
        json={"code": "HR_LETTER", "category": "HR"},
    )

    assert response.status_code == 403


def test_versions_increment_and_new_publish_retires_previous(client: TestClient) -> None:
    admin_headers = login(client, "admin")
    request_type = _create_type(client, admin_headers)

    first = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=_version_payload("Laptop Request v1"),
    )
    assert first.status_code == 201
    assert first.json()["version"] == 1

    first_publish = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1/publish",
        headers=admin_headers,
    )
    assert first_publish.status_code == 200

    second = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=_version_payload("Laptop Request v2"),
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2

    second_publish = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/2/publish",
        headers=admin_headers,
    )
    assert second_publish.status_code == 200
    assert second_publish.json()["status"] == "PUBLISHED"

    versions = client.get(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
    )
    assert versions.status_code == 200
    assert [item["status"] for item in versions.json()] == ["RETIRED", "PUBLISHED"]


def test_published_version_is_immutable(client: TestClient) -> None:
    admin_headers = login(client, "admin")
    request_type = _create_type(client, admin_headers)
    client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=_version_payload(),
    )
    client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1/publish",
        headers=admin_headers,
    )

    update = client.patch(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1",
        headers=admin_headers,
        json={"title": "Changed after publish"},
    )

    assert update.status_code == 409


def test_duplicate_dynamic_form_keys_are_rejected(client: TestClient) -> None:
    admin_headers = login(client, "admin")
    request_type = _create_type(client, admin_headers)
    payload = _version_payload()
    payload["form_schema"]["sections"].append(
        {
            "title": "Duplicate",
            "fields": [
                {
                    "key": "reason",
                    "type": "text",
                    "label": "Duplicate reason",
                    "required": False,
                }
            ],
        }
    )

    response = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=payload,
    )

    assert response.status_code == 422


def test_deactivated_request_type_is_hidden_from_employee_catalog(client: TestClient) -> None:
    admin_headers = login(client, "admin")
    employee_headers = login(client, "employee")
    request_type = _create_type(client, admin_headers)
    client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=admin_headers,
        json=_version_payload(),
    )
    client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1/publish",
        headers=admin_headers,
    )

    deactivate = client.patch(
        f"/api/v1/catalog/request-types/{request_type['id']}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert deactivate.status_code == 200

    catalog = client.get(
        "/api/v1/catalog/request-types",
        headers=employee_headers,
    )
    assert catalog.status_code == 200
    assert catalog.json() == []
