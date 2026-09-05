"""Explicit, repeatable demo catalog setup. Never rewrites an existing type.

Run AFTER migrations and identity seeding:
    python -m app.db.seed_catalog
"""
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.catalog import RequestType
from app.models.models import User
from app.schemas.catalog import RequestTypeCreate, RequestTypeVersionCreate
from app.services.catalog import (
    create_request_type,
    create_request_type_version,
    publish_request_type_version,
)

DEMO_SERVICES = [
    {
        "code": "IT_LAPTOP_REPLACEMENT", "category": "IT", "title": "Laptop replacement",
        "description": "Request a managed replacement device for your work.",
        "fields": [
            {"key": "reason", "type": "textarea", "label": "Reason for replacement", "required": True},
            {"key": "device", "type": "select", "label": "Preferred device", "required": True,
             "options": [{"value": "windows", "label": "Windows laptop"}, {"value": "macos", "label": "MacBook"}]},
            {"key": "cost_center", "type": "text", "label": "Cost center", "required": True},
            {"key": "needed_by", "type": "date", "label": "Needed by"},
        ],
    },
    {
        "code": "IT_SOFTWARE_ACCESS", "category": "IT", "title": "Software access",
        "description": "Explain the application and access level needed for your work.",
        "fields": [
            {"key": "application", "type": "text", "label": "Application", "required": True},
            {"key": "access_level", "type": "select", "label": "Access level", "required": True,
             "options": [{"value": "standard", "label": "Standard user"}, {"value": "elevated", "label": "Elevated access"}]},
            {"key": "justification", "type": "textarea", "label": "Business justification", "required": True},
            {"key": "temporary", "type": "boolean", "label": "Temporary access?", "required": True},
        ],
    },
    {
        "code": "FINANCE_REIMBURSEMENT", "category": "Finance", "title": "Expense reimbursement",
        "description": "Record business expenses. Receipt uploads will be available in the attachments phase.",
        "fields": [
            {"key": "amount", "type": "currency", "label": "Amount", "required": True},
            {"key": "currency", "type": "select", "label": "Currency", "required": True,
             "options": [{"value": "VND", "label": "VND"}, {"value": "USD", "label": "USD"}]},
            {"key": "expense_date", "type": "date", "label": "Expense date", "required": True},
            {"key": "purpose", "type": "textarea", "label": "Business purpose", "required": True},
        ],
    },
]


def seed_catalog(db: Session) -> int:
    admin = db.query(User).filter(User.email == "admin@centralops.demo", User.is_active.is_(True)).first()
    if admin is None:
        raise RuntimeError("Seed the demo identity data first; no active demo admin was found.")
    created = 0
    for item in DEMO_SERVICES:
        if db.query(RequestType).filter_by(code=item["code"]).first():
            continue
        kind = create_request_type(db, RequestTypeCreate(code=item["code"], category=item["category"]))
        version = create_request_type_version(db, kind.id, RequestTypeVersionCreate(
            title=item["title"], description=item["description"],
            form_schema={"sections": [{"title": "Request details", "fields": item["fields"]}]},
        ), admin)
        publish_request_type_version(db, kind.id, version.version)
        created += 1
    db.commit()
    return created


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"Created {seed_catalog(session)} demo request types; existing types left unchanged.")
