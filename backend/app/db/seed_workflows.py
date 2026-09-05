"""Explicit LOCAL DEMO setup: Manager -> Central Service Lead for known services.

Run after identity and catalog seed. Existing definitions are never overwritten.
This is demo routing, not a claim about any employer's approval policy.
"""
from sqlalchemy.orm import Session

from app.db.seed_catalog import DEMO_SERVICES
from app.db.session import SessionLocal
from app.models.catalog import RequestType
from app.models.models import ServiceTeam, User
from app.models.workflows import WorkflowDefinition
from app.schemas.workflows import WorkflowCreate, WorkflowVersionInput
from app.services.workflows import create_definition, create_version, publish_version


def seed_workflows(db: Session) -> int:
    admin = db.query(User).filter_by(email="admin@centralops.demo", is_active=True).first()
    team = db.query(ServiceTeam).filter_by(code="CENTRAL_SERVICE", is_active=True).first()
    if not admin or not team:
        raise RuntimeError("Seed demo identity and service-team data first.")
    count = 0
    for item in DEMO_SERVICES:
        kind = db.query(RequestType).filter_by(code=item["code"]).first()
        if not kind:
            raise RuntimeError("Run python -m app.db.seed_catalog first.")
        if db.query(WorkflowDefinition).filter_by(request_type_id=kind.id).first():
            continue
        definition = create_definition(db, admin, WorkflowCreate(
            code=f"DEMO_{kind.code}", name=f"{item['title']} approval", request_type_id=kind.id,
        ))
        create_version(db, admin, definition.id, WorkflowVersionInput(steps=[
            {"name": "Line manager approval", "approver_resolver_type": "MANAGER"},
            {"name": "Service lead approval", "approver_resolver_type": "TEAM_LEAD",
             "approver_resolver_config": {"service_team_id": team.id}},
        ]))
        publish_version(db, admin, definition.id, 1)
        count += 1
    db.commit()
    return count


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Created {seed_workflows(session)} demo workflows; existing definitions left unchanged.")
