from datetime import UTC, datetime

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
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


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        raise CatalogConflictError("Catalog changed concurrently; reload and retry.") from exc


def _lock_type(db: Session, request_type_id: int) -> RequestType:
    request_type = db.query(RequestType).filter(RequestType.id == request_type_id).with_for_update().first()
    if request_type is None:
        raise CatalogNotFoundError("Request type not found")
    return request_type


def create_request_type(db: Session, payload: RequestTypeCreate) -> RequestType:
    if db.query(RequestType).filter(RequestType.code == payload.code).first():
        raise CatalogConflictError("Request type code already exists")
    if payload.owner_service_team_id is not None and not db.get(ServiceTeam, payload.owner_service_team_id):
        raise CatalogNotFoundError("Service team not found")
    request_type = RequestType(**payload.model_dump())
    db.add(request_type)
    _flush(db)
    return request_type


def update_request_type(db: Session, request_type_id: int, payload: RequestTypeUpdate) -> RequestType:
    request_type = _lock_type(db, request_type_id)
    changes = payload.model_dump(exclude_unset=True)
    team_id = changes.get("owner_service_team_id")
    if team_id is not None and not db.get(ServiceTeam, team_id):
        raise CatalogNotFoundError("Service team not found")
    for field, value in changes.items():
        setattr(request_type, field, value)
    _flush(db)
    return request_type


def create_request_type_version(
    db: Session, request_type_id: int, payload: RequestTypeVersionCreate, actor: User,
) -> RequestTypeVersion:
    _lock_type(db, request_type_id)
    latest = db.query(func.max(RequestTypeVersion.version)).filter(
        RequestTypeVersion.request_type_id == request_type_id,
    ).scalar() or 0
    version = RequestTypeVersion(
        request_type_id=request_type_id, version=latest + 1,
        **payload.model_dump(mode="json"), status="DRAFT", created_by=actor.id,
    )
    db.add(version)
    _flush(db)
    return version


def update_request_type_version(
    db: Session, request_type_id: int, version_number: int, payload: RequestTypeVersionUpdate,
) -> RequestTypeVersion:
    _lock_type(db, request_type_id)
    version = _get_version(db, request_type_id, version_number)
    if version.status != "DRAFT":
        raise CatalogConflictError("Published or retired request type versions are immutable")
    # model_dump already serializes nested form_schema to a dict. Do not
    # call .model_dump() on that dictionary a second time.
    for field, value in payload.model_dump(exclude_unset=True, mode="json").items():
        setattr(version, field, value)
    _flush(db)
    return version


def publish_request_type_version(
    db: Session, request_type_id: int, version_number: int,
) -> RequestTypeVersion:
    _lock_type(db, request_type_id)
    target = _get_version(db, request_type_id, version_number)
    if target.status == "PUBLISHED":
        return target
    if target.status != "DRAFT":
        raise CatalogConflictError("Only draft versions can be published")
    previous = db.query(RequestTypeVersion).filter(
        RequestTypeVersion.request_type_id == request_type_id,
        RequestTypeVersion.status == "PUBLISHED",
    ).all()
    for version in previous:
        version.status = "RETIRED"
    # Release the unique partial-index entry before publishing the next row.
    _flush(db)
    target.status = "PUBLISHED"
    target.published_at = datetime.now(UTC)
    _flush(db)
    return target


def list_request_type_versions(db: Session, request_type_id: int) -> list[RequestTypeVersion]:
    if not db.get(RequestType, request_type_id):
        raise CatalogNotFoundError("Request type not found")
    return db.query(RequestTypeVersion).filter(
        RequestTypeVersion.request_type_id == request_type_id,
    ).order_by(RequestTypeVersion.version.asc()).all()


def list_published_catalog(db: Session) -> list[tuple[RequestType, RequestTypeVersion]]:
    return db.query(RequestType, RequestTypeVersion).join(
        RequestTypeVersion, RequestTypeVersion.request_type_id == RequestType.id,
    ).filter(
        RequestType.is_active.is_(True), RequestTypeVersion.status == "PUBLISHED",
    ).order_by(RequestType.category.asc(), RequestType.code.asc()).all()


def _get_version(db: Session, request_type_id: int, version_number: int) -> RequestTypeVersion:
    version = db.query(RequestTypeVersion).filter(
        RequestTypeVersion.request_type_id == request_type_id,
        RequestTypeVersion.version == version_number,
    ).populate_existing().first()
    if version is None:
        raise CatalogNotFoundError("Request type version not found")
    return version
