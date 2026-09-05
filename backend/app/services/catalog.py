from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import ServiceTeam, User
from app.schemas.catalog import (
    RequestTypeCreate,
    RequestTypeUpdate,
    RequestTypeVersionCreate,
    RequestTypeVersionUpdate,
)


class CatalogError(Exception):
    pass


class CatalogNotFoundError(CatalogError):
    pass


class CatalogConflictError(CatalogError):
    pass


def create_request_type(db: Session, payload: RequestTypeCreate) -> RequestType:
    if db.query(RequestType).filter(RequestType.code == payload.code).first():
        raise CatalogConflictError("Request type code already exists")

    if payload.owner_service_team_id is not None:
        team = db.get(ServiceTeam, payload.owner_service_team_id)
        if not team:
            raise CatalogNotFoundError("Service team not found")

    request_type = RequestType(**payload.model_dump())
    db.add(request_type)
    db.flush()
    return request_type


def update_request_type(
    db: Session,
    request_type_id: int,
    payload: RequestTypeUpdate,
) -> RequestType:
    request_type = db.get(RequestType, request_type_id)
    if not request_type:
        raise CatalogNotFoundError("Request type not found")

    changes = payload.model_dump(exclude_unset=True)
    owner_service_team_id = changes.get("owner_service_team_id")
    if owner_service_team_id is not None and not db.get(ServiceTeam, owner_service_team_id):
        raise CatalogNotFoundError("Service team not found")

    for field, value in changes.items():
        setattr(request_type, field, value)
    db.flush()
    return request_type


def create_request_type_version(
    db: Session,
    request_type_id: int,
    payload: RequestTypeVersionCreate,
    actor: User,
) -> RequestTypeVersion:
    request_type = db.get(RequestType, request_type_id)
    if not request_type:
        raise CatalogNotFoundError("Request type not found")

    latest_version = (
        db.query(func.max(RequestTypeVersion.version))
        .filter(RequestTypeVersion.request_type_id == request_type_id)
        .scalar()
        or 0
    )

    version = RequestTypeVersion(
        request_type_id=request_type_id,
        version=latest_version + 1,
        title=payload.title,
        description=payload.description,
        form_schema=payload.form_schema.model_dump(mode="json"),
        validation_schema=payload.validation_schema,
        sla_config=payload.sla_config,
        attachment_config=payload.attachment_config,
        status="DRAFT",
        created_by=actor.id,
    )
    db.add(version)
    db.flush()
    return version


def update_request_type_version(
    db: Session,
    request_type_id: int,
    version_number: int,
    payload: RequestTypeVersionUpdate,
) -> RequestTypeVersion:
    version = _get_version(db, request_type_id, version_number)
    if version.status != "DRAFT":
        raise CatalogConflictError("Published or retired request type versions are immutable")

    changes = payload.model_dump(exclude_unset=True)
    form_schema = changes.pop("form_schema", None)
    if form_schema is not None:
        version.form_schema = form_schema.model_dump(mode="json")

    for field, value in changes.items():
        setattr(version, field, value)
    db.flush()
    return version


def publish_request_type_version(
    db: Session,
    request_type_id: int,
    version_number: int,
) -> RequestTypeVersion:
    target = _get_version(db, request_type_id, version_number)
    if target.status == "PUBLISHED":
        return target
    if target.status != "DRAFT":
        raise CatalogConflictError("Only draft versions can be published")

    published_versions = (
        db.query(RequestTypeVersion)
        .filter(
            RequestTypeVersion.request_type_id == request_type_id,
            RequestTypeVersion.status == "PUBLISHED",
        )
        .all()
    )
    for current in published_versions:
        current.status = "RETIRED"

    target.status = "PUBLISHED"
    target.published_at = datetime.now(UTC)
    db.flush()
    return target


def list_request_type_versions(db: Session, request_type_id: int) -> list[RequestTypeVersion]:
    if not db.get(RequestType, request_type_id):
        raise CatalogNotFoundError("Request type not found")
    return (
        db.query(RequestTypeVersion)
        .filter(RequestTypeVersion.request_type_id == request_type_id)
        .order_by(RequestTypeVersion.version.asc())
        .all()
    )


def list_published_catalog(db: Session) -> list[tuple[RequestType, RequestTypeVersion]]:
    return (
        db.query(RequestType, RequestTypeVersion)
        .join(RequestTypeVersion, RequestTypeVersion.request_type_id == RequestType.id)
        .filter(
            RequestType.is_active.is_(True),
            RequestTypeVersion.status == "PUBLISHED",
        )
        .order_by(RequestType.category.asc(), RequestType.code.asc())
        .all()
    )


def _get_version(db: Session, request_type_id: int, version_number: int) -> RequestTypeVersion:
    version = (
        db.query(RequestTypeVersion)
        .filter(
            RequestTypeVersion.request_type_id == request_type_id,
            RequestTypeVersion.version == version_number,
        )
        .first()
    )
    if not version:
        raise CatalogNotFoundError("Request type version not found")
    return version
