from typing import NoReturn

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.models import User
from app.schemas.catalog import (
    CatalogRequestTypeOut,
    RequestTypeCreate,
    RequestTypeOut,
    RequestTypeUpdate,
    RequestTypeVersionCreate,
    RequestTypeVersionOut,
    RequestTypeVersionUpdate,
)
from app.services.audit import record_audit
from app.services.catalog import (
    CatalogConflictError,
    CatalogNotFoundError,
    create_request_type,
    create_request_type_version,
    list_published_catalog,
    list_request_type_versions,
    publish_request_type_version,
    update_request_type,
    update_request_type_version,
)

router = APIRouter()


def _raise_catalog_error(exc: Exception) -> NoReturn:
    if isinstance(exc, CatalogNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, CatalogConflictError):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    raise exc


@router.get("/request-types", response_model=list[CatalogRequestTypeOut])
def list_catalog(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[CatalogRequestTypeOut]:
    return [
        CatalogRequestTypeOut(
            id=request_type.id,
            code=request_type.code,
            category=request_type.category,
            owner_service_team_id=request_type.owner_service_team_id,
            is_active=request_type.is_active,
            created_at=request_type.created_at,
            published_version=RequestTypeVersionOut.model_validate(version),
        )
        for request_type, version in list_published_catalog(db)
    ]


@router.post(
    "/request-types",
    response_model=RequestTypeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_type(
    payload: RequestTypeCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> RequestTypeOut:
    try:
        request_type = create_request_type(db, payload)
        record_audit(db, "catalog_type_changed", actor_id=actor.id, resource_type="request_type",
                     resource_id=request_type.id, details={"request_type_id": request_type.id, "active": request_type.is_active})
        db.commit()
        db.refresh(request_type)
        return RequestTypeOut.model_validate(request_type)
    except (CatalogNotFoundError, CatalogConflictError) as exc:
        db.rollback()
        _raise_catalog_error(exc)


@router.patch("/request-types/{request_type_id}", response_model=RequestTypeOut)
def update_type(
    request_type_id: int,
    payload: RequestTypeUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> RequestTypeOut:
    try:
        request_type = update_request_type(db, request_type_id, payload)
        record_audit(db, "catalog_type_changed", actor_id=actor.id, resource_type="request_type",
                     resource_id=request_type.id, details={"request_type_id": request_type.id, "active": request_type.is_active})
        db.commit()
        db.refresh(request_type)
        return RequestTypeOut.model_validate(request_type)
    except (CatalogNotFoundError, CatalogConflictError) as exc:
        db.rollback()
        _raise_catalog_error(exc)


@router.post(
    "/request-types/{request_type_id}/versions",
    response_model=RequestTypeVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_version(
    request_type_id: int,
    payload: RequestTypeVersionCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> RequestTypeVersionOut:
    try:
        version = create_request_type_version(db, request_type_id, payload, actor)
        record_audit(db, "catalog_version_published" if version.status == "PUBLISHED" else "catalog_version_changed",
                     actor_id=actor.id, resource_type="request_type_version", resource_id=version.id,
                     details={"request_type_id": request_type_id, "version_id": version.id})
        db.commit()
        db.refresh(version)
        return RequestTypeVersionOut.model_validate(version)
    except (CatalogNotFoundError, CatalogConflictError) as exc:
        db.rollback()
        _raise_catalog_error(exc)


@router.get(
    "/request-types/{request_type_id}/versions",
    response_model=list[RequestTypeVersionOut],
)
def list_versions(
    request_type_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN")),
) -> list[RequestTypeVersionOut]:
    try:
        versions = list_request_type_versions(db, request_type_id)
        return [RequestTypeVersionOut.model_validate(version) for version in versions]
    except CatalogNotFoundError as exc:
        _raise_catalog_error(exc)


@router.patch(
    "/request-types/{request_type_id}/versions/{version_number}",
    response_model=RequestTypeVersionOut,
)
def update_version(
    request_type_id: int,
    version_number: int,
    payload: RequestTypeVersionUpdate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> RequestTypeVersionOut:
    try:
        version = update_request_type_version(db, request_type_id, version_number, payload)
        record_audit(db, "catalog_version_published" if version.status == "PUBLISHED" else "catalog_version_changed",
                     actor_id=actor.id, resource_type="request_type_version", resource_id=version.id,
                     details={"request_type_id": request_type_id, "version_id": version.id})
        db.commit()
        db.refresh(version)
        return RequestTypeVersionOut.model_validate(version)
    except (CatalogNotFoundError, CatalogConflictError) as exc:
        db.rollback()
        _raise_catalog_error(exc)


@router.post(
    "/request-types/{request_type_id}/versions/{version_number}/publish",
    response_model=RequestTypeVersionOut,
)
def publish_version(
    request_type_id: int,
    version_number: int,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> RequestTypeVersionOut:
    try:
        version = publish_request_type_version(db, request_type_id, version_number)
        record_audit(db, "catalog_version_published" if version.status == "PUBLISHED" else "catalog_version_changed",
                     actor_id=actor.id, resource_type="request_type_version", resource_id=version.id,
                     details={"request_type_id": request_type_id, "version_id": version.id})
        db.commit()
        db.refresh(version)
        return RequestTypeVersionOut.model_validate(version)
    except (CatalogNotFoundError, CatalogConflictError) as exc:
        db.rollback()
        _raise_catalog_error(exc)
