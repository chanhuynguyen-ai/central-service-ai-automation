"""Private draft editing over the existing ServiceRequest aggregate.

No approval, AI call, SLA clock or external notification is started here.
Mutations and their audit event are committed together by the API route.
"""
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AuditEvent, ServiceRequest, User
from app.schemas.catalog import DynamicFormSchema, RequestTypeVersionOut
from app.schemas.drafts import DraftCreate, DraftOut, DraftUpdate
from app.services.form_validation import validate_draft, validate_form_data


class DraftError(Exception):
    def __init__(self, status_code: int, detail: str | list[dict]) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(str(detail))


def _schema(version: RequestTypeVersion) -> DynamicFormSchema:
    try:
        return DynamicFormSchema.model_validate(version.form_schema)
    except ValidationError as exc:
        raise DraftError(409, "This form version is not supported by the draft editor.") from exc


def owned_draft(db: Session, request_id: int, actor: User) -> ServiceRequest:
    draft = db.query(ServiceRequest).filter(
        ServiceRequest.id == request_id,
        ServiceRequest.requester_id == actor.id,
        ServiceRequest.status.in_(["draft", "changes_requested"]),
    ).first()
    if draft is None:
        raise DraftError(404, "Draft not found")
    return draft


def draft_output(db: Session, draft: ServiceRequest) -> DraftOut:
    version = db.get(RequestTypeVersion, draft.request_type_version_id)
    if version is None:
        raise DraftError(409, "Request type version is unavailable")
    validation = validate_draft(
        draft.title, draft.description, _schema(version), draft.form_data,
        db=db, validation_schema=version.validation_schema,
    )
    return DraftOut(
        id=draft.id, reference=draft.reference, title=draft.title, status=draft.status,
        description=draft.description, request_type_version_id=version.id,
        revision=draft.draft_revision, form_data=draft.form_data,
        updated_at=draft.updated_at,
        request_type_version=RequestTypeVersionOut.model_validate(version),
        validation=validation,
    )


def _clean_data(db: Session, version: RequestTypeVersion, data: dict) -> dict:
    cleaned, errors = validate_form_data(_schema(version), data, require_complete=False, db=db)
    if errors:
        raise DraftError(422, [error.model_dump() for error in errors])
    return cleaned


def _audit(db: Session, draft: ServiceRequest, actor: User, event: str) -> None:
    db.add(AuditEvent(
        request_id=draft.id, actor_id=actor.id, event_type=event,
        details={"request_type_version_id": draft.request_type_version_id,
                 "revision": draft.draft_revision},
    ))


def create_draft(db: Session, actor: User, payload: DraftCreate) -> ServiceRequest:
    version = db.get(RequestTypeVersion, payload.request_type_version_id)
    if version is None:
        raise DraftError(404, "Request type version not found")
    request_type = db.get(RequestType, version.request_type_id)
    if request_type is None or not request_type.is_active or version.status != "PUBLISHED":
        raise DraftError(409, "Select an active published service from the catalog.")
    draft = ServiceRequest(
        reference=f"DRF-{uuid4().hex[:24]}",
        requester_id=actor.id, department=actor.department,
        title=payload.title.strip(), description=payload.description.strip(),
        category=request_type.category, priority="medium", status="draft",
        request_type_version_id=version.id, form_data=_clean_data(db, version, payload.form_data),
        draft_revision=1, submitted_at=None, due_at=None,
    )
    db.add(draft)
    db.flush()
    _audit(db, draft, actor, "draft_created")
    return draft


def update_draft(
    db: Session, actor: User, request_id: int, payload: DraftUpdate,
) -> ServiceRequest:
    draft = owned_draft(db, request_id, actor)
    version = db.get(RequestTypeVersion, draft.request_type_version_id)
    if version is None:
        raise DraftError(409, "Request type version is unavailable")
    cleaned = _clean_data(db, version, payload.form_data)
    # Compare-and-swap protects against lost updates, even on SQLite. No
    # SELECT-then-unconditional-UPDATE and no dependency on a row lock here.
    result = db.execute(update(ServiceRequest).where(
        ServiceRequest.id == request_id,
        ServiceRequest.requester_id == actor.id,
        ServiceRequest.status.in_(["draft", "changes_requested"]),
        ServiceRequest.draft_revision == payload.revision,
    ).values(
        title=payload.title.strip(), description=payload.description.strip(),
        form_data=cleaned, draft_revision=payload.revision + 1,
        updated_at=datetime.now(UTC),
    ).execution_options(synchronize_session=False))
    if result.rowcount != 1:
        raise DraftError(409, "Draft changed in another window. Reload before saving.")
    db.refresh(draft)
    _audit(db, draft, actor, "draft_updated")
    return draft
