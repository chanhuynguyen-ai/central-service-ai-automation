from app.models.models import AuditEvent, Role, User, UserRole
from tests.test_activity import endpoint, post
from tests.test_workflows import database, setup_flow, submit, user_login


def test_auditor_plus_unrelated_manager_does_not_expand_comment_write_scope(client):
    _, owner, _, _, draft = setup_flow(client)
    submit(client, owner, draft)
    with database(client) as db:
        user = db.query(User).filter_by(email="manager.operations@centralops.demo").one()
        role = db.query(Role).filter_by(code="AUDITOR").one()
        db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()
    unrelated = user_login(client, "manager.operations@centralops.demo")
    access = client.get(endpoint(draft, "permissions"), headers=unrelated)
    assert access.status_code == 200
    assert access.json() == {"can_comment": False, "can_read_internal": True, "can_write_internal": False}
    assert post(client, draft, unrelated).status_code == 403
    assert post(client, draft, unrelated, visibility="INTERNAL").status_code == 403


def test_catalog_publication_and_workflow_configuration_are_safely_audited(client):
    admin, _, _, definition_id, _ = setup_flow(client)
    catalog = client.get("/api/v1/audit/events?event_type=catalog_version_published", headers=admin).json()
    assert len(catalog["items"]) == 1
    row = catalog["items"][0]
    assert row["resource_type"] == "request_type_version"
    assert row["resource_id"] == str(row["details"]["version_id"])
    assert set(row["details"]) == {"version_id", "request_type_id"}
    assert client.patch(f"/api/v1/workflows/definitions/{definition_id}", headers=admin,
                        json={"is_active": False}).status_code == 200
    with database(client) as db:
        rows = db.query(AuditEvent).filter(AuditEvent.event_type.like("workflow_%")).all()
        assert {row.event_type for row in rows} >= {"workflow_definition_created", "workflow_version_created", "workflow_version_published", "workflow_activation_changed"}
        assert "form_schema" not in str([row.details for row in rows])
