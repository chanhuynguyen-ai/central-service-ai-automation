from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.db.session import get_db
from app.models.models import AuditEvent, ServiceRequest
from tests.conftest import login

SCHEMA = {"sections": [{"title": "Details", "fields": [
    {"key": "reason", "type": "textarea", "label": "Reason", "required": True},
    {"key": "urgent", "type": "boolean", "label": "Urgent", "required": True},
    {"key": "amount", "type": "currency", "label": "Amount"},
]}]}


def published_service(client: TestClient):
    admin = login(client, "admin")
    response = client.post("/api/v1/catalog/request-types", headers=admin, json={"code": "TEST_DRAFT", "category": "IT"})
    assert response.status_code == 201
    type_id = response.json()["id"]
    version = client.post(f"/api/v1/catalog/request-types/{type_id}/versions", headers=admin, json={"title": "Test service", "form_schema": SCHEMA})
    assert version.status_code == 201
    response = client.post(f"/api/v1/catalog/request-types/{type_id}/versions/1/publish", headers=admin)
    assert response.status_code == 200
    return admin, type_id, version.json()["id"]


def new_draft(client, owner, version_id):
    result = client.post("/api/v1/requests/drafts", headers=owner, json={"request_type_version_id": version_id})
    assert result.status_code == 201, result.text
    return result.json()


def test_draft_is_private_incomplete_and_has_no_submission_clock(client: TestClient):
    admin, _, version_id = published_service(client)
    owner = login(client)
    draft = new_draft(client, owner, version_id)
    assert not draft["validation"]["valid"]
    assert "reason" in draft["validation"]["missing_fields"]
    assert client.get("/api/v1/requests/drafts", headers=owner).json()["total"] == 1
    for headers in (login(client, "employee2"), admin):
        assert client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=headers).status_code == 404
        assert client.get("/api/v1/requests/drafts", headers=headers).json()["total"] == 0
        assert client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=headers, json={"revision": 1}).status_code == 404
        assert client.post(f"/api/v1/requests/drafts/{draft['id']}/validate", headers=headers).status_code == 404
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        row = db.get(ServiceRequest, draft["id"])
        assert row.submitted_at is None and row.due_at is None
        assert row.ai_summary is None
        assert db.query(AuditEvent).filter_by(request_id=row.id, event_type="draft_created").count() == 1
    finally:
        generator.close()


def test_save_validate_and_stale_revision_conflict(client: TestClient):
    _, _, version_id = published_service(client)
    owner = login(client)
    draft = new_draft(client, owner, version_id)
    values = {"revision": 1, "title": "Replace laptop", "description": "Laptop keeps shutting down during client meetings.", "form_data": {"reason": "Device failure", "urgent": False, "amount": "10.1"}}
    saved = client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=owner, json=values)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == 2
    assert saved.json()["form_data"]["amount"] == "10.10"
    assert saved.json()["validation"]["valid"]
    values["title"] = "Stale overwrite"
    assert client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=owner, json=values).status_code == 409
    read = client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=owner).json()
    assert read["title"] == "Replace laptop"
    assert client.post(f"/api/v1/requests/drafts/{draft['id']}/validate", headers=owner).json()["valid"]


def test_pinned_version_survives_new_publication(client: TestClient):
    admin, type_id, version_id = published_service(client)
    owner = login(client)
    draft = new_draft(client, owner, version_id)
    schema2 = deepcopy(SCHEMA)
    schema2["sections"][0]["fields"].append({"key": "extra", "type": "text", "label": "Extra", "required": True})
    assert client.post(f"/api/v1/catalog/request-types/{type_id}/versions", headers=admin, json={"title": "New version", "form_schema": schema2}).status_code == 201
    assert client.post(f"/api/v1/catalog/request-types/{type_id}/versions/2/publish", headers=admin).status_code == 200
    old = client.get(f"/api/v1/requests/drafts/{draft['id']}", headers=owner).json()
    assert old["request_type_version_id"] == version_id
    assert old["request_type_version"]["status"] == "RETIRED"
    assert "extra" not in old["validation"]["missing_fields"]
    assert client.post("/api/v1/requests/drafts", headers=owner, json={"request_type_version_id": version_id}).status_code == 409
    assert client.put(f"/api/v1/requests/drafts/{draft['id']}", headers=owner, json={"revision": 1, "form_data": {"reason": "Still editable"}}).status_code == 200


def test_draft_not_exposed_to_legacy_routes_assistant_or_analytics(client: TestClient):
    admin, _, version_id = published_service(client)
    owner = login(client)
    before = client.get("/api/v1/analytics/summary", headers=admin).json()
    draft = new_draft(client, owner, version_id)
    for headers in (owner, admin):
        assert client.get(f"/api/v1/requests/{draft['id']}", headers=headers).status_code == 404
        ids = {item["id"] for item in client.get("/api/v1/requests", headers=headers).json()["items"]}
        assert draft["id"] not in ids
        assert client.post("/api/v1/assistant/chat", headers=headers, json={"question": "What is the current request status?", "request_reference": draft["reference"]}).status_code == 404
    assert client.patch(f"/api/v1/requests/{draft['id']}/status", headers=admin, json={"status": "completed"}).status_code == 404
    assert client.post(f"/api/v1/requests/{draft['id']}/decision", headers=admin, json={"decision": "approve"}).status_code == 404
    assert client.get("/api/v1/analytics/summary", headers=admin).json()["total_requests"] == before["total_requests"]


@pytest.mark.parametrize("data", [{"unknown": 1}, {"urgent": "false"}, {"amount": 1.25}, {"reason": {"bad": True}}])
def test_invalid_values_rejected_at_save(client: TestClient, data):
    _, _, version_id = published_service(client)
    owner = login(client)
    result = client.post("/api/v1/requests/drafts", headers=owner, json={"request_type_version_id": version_id, "form_data": data})
    assert result.status_code == 422
    assert client.get("/api/v1/requests/drafts", headers=owner).json()["total"] == 0


def test_overposting_and_unauthenticated_calls(client: TestClient):
    assert client.get("/api/v1/requests/drafts").status_code == 401
    _, _, version_id = published_service(client)
    response = client.post("/api/v1/requests/drafts", headers=login(client), json={"request_type_version_id": version_id, "requester_id": 99})
    assert response.status_code == 422


def test_update_form_schema_is_serialized_once(client: TestClient):
    admin = login(client, "admin")
    kind = client.post("/api/v1/catalog/request-types", headers=admin, json={"code": "FORM_UPDATE", "category": "IT"}).json()
    url = f"/api/v1/catalog/request-types/{kind['id']}/versions"
    assert client.post(url, headers=admin, json={"title": "Draft config", "form_schema": SCHEMA}).status_code == 201
    response = client.patch(url + "/1", headers=admin, json={"form_schema": SCHEMA, "title": "Changed config"})
    assert response.status_code == 200, response.text
    assert response.json()["form_schema"]["sections"][0]["fields"][0]["key"] == "reason"


def test_demo_catalog_seed_is_idempotent(client: TestClient):
    from app.db.seed_catalog import seed_catalog
    from app.models.catalog import RequestTypeVersion

    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    try:
        assert seed_catalog(db) == 3
        assert seed_catalog(db) == 0
        assert db.query(RequestTypeVersion).count() == 3
    finally:
        generator.close()
    catalog = client.get("/api/v1/catalog/request-types", headers=login(client)).json()
    assert len(catalog) == 3


def test_picker_options_are_authenticated_and_minimal(client: TestClient):
    assert client.get("/api/v1/requests/drafts/lookups").status_code == 401
    result = client.get("/api/v1/requests/drafts/lookups", headers=login(client))
    assert result.status_code == 200
    assert result.json()["users"]
    assert set(result.json()["users"][0]) == {"id", "name"}
