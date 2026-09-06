from fastapi.testclient import TestClient

from tests.conftest import login


def _publish_type(
    client: TestClient,
    headers: dict[str, str],
    *,
    code: str,
    category: str,
    title: str,
    description: str,
    fields: list[dict],
) -> dict:
    created = client.post(
        "/api/v1/catalog/request-types",
        headers=headers,
        json={"code": code, "category": category, "is_active": True},
    )
    assert created.status_code == 201
    request_type = created.json()
    version = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions",
        headers=headers,
        json={
            "title": title,
            "description": description,
            "form_schema": {"sections": [{"title": "Request details", "fields": fields}]},
        },
    )
    assert version.status_code == 201
    published = client.post(
        f"/api/v1/catalog/request-types/{request_type['id']}/versions/1/publish",
        headers=headers,
    )
    assert published.status_code == 200
    return published.json()


def _seed_catalog(client: TestClient) -> None:
    admin = login(client, "admin")
    _publish_type(
        client,
        admin,
        code="IT_LAPTOP",
        category="IT",
        title="Laptop replacement request",
        description="Replace a failing company laptop used for business work.",
        fields=[
            {"key": "reason", "type": "textarea", "label": "Reason", "required": True},
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
            {"key": "cost_center", "type": "text", "label": "Cost center", "required": True},
        ],
    )
    _publish_type(
        client,
        admin,
        code="HR_LETTER",
        category="HR",
        title="Employment letter",
        description="Request an HR employment confirmation letter.",
        fields=[
            {"key": "purpose", "type": "textarea", "label": "Purpose", "required": True},
        ],
    )


def test_ai_intake_classifies_only_published_catalog(client: TestClient) -> None:
    _seed_catalog(client)
    employee = login(client, "employee")

    response = client.post(
        "/api/v1/ai/intake/classify",
        headers=employee,
        json={"text": "My company laptop keeps failing and I need a replacement for client work."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_type_code"] == "IT_LAPTOP"
    assert body["request_type_version_id"] > 0
    assert body["provider"] == "mock"
    assert body["needs_human_confirmation"] is True
    assert all(item["request_type_code"] != "IT_LAPTOP" for item in body["alternatives"])


def test_ai_intake_extracts_known_values_and_computes_missing_fields_deterministically(
    client: TestClient,
) -> None:
    _seed_catalog(client)
    employee = login(client, "employee")

    response = client.post(
        "/api/v1/ai/intake/draft",
        headers=employee,
        json={
            "text": "My laptop is failing during client work. This is high urgency.",
            "request_type_code": "IT_LAPTOP",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_type_code"] == "IT_LAPTOP"
    assert body["extracted_fields"]["urgency"] == "high"
    assert "reason" in body["extracted_fields"]
    assert body["missing_required_fields"] == ["cost_center"]
    assert body["needs_human_confirmation"] is True


def test_ai_intake_rejects_unpublished_or_unknown_override(client: TestClient) -> None:
    _seed_catalog(client)
    employee = login(client, "employee")

    response = client.post(
        "/api/v1/ai/intake/draft",
        headers=employee,
        json={"text": "I need something", "request_type_code": "SECRET_ADMIN_TYPE"},
    )

    assert response.status_code == 404


def test_ai_intake_requires_authentication(client: TestClient) -> None:
    response = client.post(
        "/api/v1/ai/intake/classify",
        json={"text": "My laptop is broken"},
    )

    assert response.status_code == 401
