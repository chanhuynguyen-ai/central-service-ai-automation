from collections.abc import Generator
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.attachments import (
    AttachmentCompleteInput,
    AttachmentDownloadOut,
    AttachmentOut,
    AttachmentPresignInput,
    AttachmentPresignOut,
)
from app.services import attachments as service

router = APIRouter()


@contextmanager
def transaction(db: Session) -> Generator[None, None, None]:
    try:
        yield
        db.commit()
    except service.AttachmentError as exc:
        db.rollback()
        raise HTTPException(exc.status_code, exc.detail) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Conflicting attachment operation; reload and retry.") from exc


@router.get("/{request_id}/attachments", response_model=list[AttachmentOut])
def list_request_attachments(
    request_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    try:
        return [AttachmentOut.model_validate(row) for row in service.list_attachments(db, actor, request_id)]
    except service.AttachmentError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post(
    "/{request_id}/attachments/presign",
    response_model=AttachmentPresignOut,
    status_code=201,
)
def presign_attachment(
    request_id: int,
    payload: AttachmentPresignInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    with transaction(db):
        row, reservation = service.create_pending(db, actor, request_id, payload)
        return AttachmentPresignOut(
            attachment_id=row.id,
            upload_url=str(reservation["url"]),
            form_fields={str(key): str(value) for key, value in dict(reservation["fields"]).items()},
            expires_in_seconds=settings.s3_presign_expiry_seconds,
        )


@router.post(
    "/{request_id}/attachments/{attachment_id}/complete",
    response_model=AttachmentOut,
)
def complete_attachment(
    request_id: int,
    attachment_id: int,
    _: AttachmentCompleteInput,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    with transaction(db):
        row = service.complete(db, actor, request_id, attachment_id)
        return AttachmentOut.model_validate(service._output(db, row))


@router.post(
    "/{request_id}/attachments/{attachment_id}/download",
    response_model=AttachmentDownloadOut,
)
def create_download_url(
    request_id: int,
    attachment_id: int,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
):
    with transaction(db):
        url = service.download_url(db, actor, request_id, attachment_id)
        return AttachmentDownloadOut(
            download_url=url,
            expires_in_seconds=settings.s3_presign_expiry_seconds,
        )
