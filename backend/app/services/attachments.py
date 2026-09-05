"""Authorized request attachment lifecycle.

The database owns attachment state. S3/MinIO stores bytes. Routes own commits.
"""
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.attachments import RequestAttachment
from app.models.fulfillment import ServiceWorkItem
from app.models.models import ServiceRequest, ServiceTeam, ServiceTeamMember, User
from app.schemas.attachments import AttachmentPresignInput
from app.services import storage
from app.services.audit import record_audit
from app.services.permissions import user_has_any_role
from app.services.workflows import WorkflowError, visible_request


class AttachmentError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _service_scope(db: Session, actor: User, request_id: int) -> bool:
    item = db.query(ServiceWorkItem).filter_by(request_id=request_id).first()
    if item is None:
        return False
    if user_has_any_role(actor, "ADMIN"):
        return True
    if not user_has_any_role(actor, "SERVICE_AGENT", "SERVICE_LEAD"):
        return False
    team = db.get(ServiceTeam, item.service_team_id)
    if team is None or not team.is_active:
        return False
    if team.lead_user_id == actor.id:
        return True
    return db.query(ServiceTeamMember).filter_by(
        service_team_id=item.service_team_id, user_id=actor.id,
    ).first() is not None


def _draft_or_visible_request(db: Session, actor: User, request_id: int) -> ServiceRequest:
    request = db.get(ServiceRequest, request_id)
    if request is None or request.request_type_version_id is None:
        raise AttachmentError(404, "Request not found")
    if request.status == "draft":
        if request.requester_id != actor.id:
            raise AttachmentError(404, "Request not found")
        return request
    if _service_scope(db, actor, request.id):
        return request
    try:
        return visible_request(db, actor, request_id)
    except WorkflowError as exc:
        raise AttachmentError(exc.status_code, str(exc.detail)) from exc


def _can_upload_internal(db: Session, actor: User, request: ServiceRequest) -> bool:
    return user_has_any_role(actor, "ADMIN") or _service_scope(db, actor, request.id)


def _can_read_attachment(
    db: Session,
    actor: User,
    request: ServiceRequest,
    attachment: RequestAttachment,
) -> bool:
    if attachment.visibility == "REQUESTER_VISIBLE":
        return True
    if request.requester_id == actor.id:
        return False
    return user_has_any_role(actor, "ADMIN", "AUDITOR") or _service_scope(db, actor, request.id)


def _output(db: Session, row: RequestAttachment) -> dict:
    uploader = db.get(User, row.uploaded_by)
    return {
        "id": row.id,
        "request_id": row.request_id,
        "uploaded_by": row.uploaded_by,
        "uploader_name": uploader.full_name if uploader else "Former user",
        "original_filename": row.original_filename,
        "mime_type": row.mime_type,
        "size_bytes": row.size_bytes,
        "sha256": row.sha256,
        "visibility": row.visibility,
        "status": row.status,
        "created_at": row.created_at,
        "ready_at": row.ready_at,
    }


def list_attachments(db: Session, actor: User, request_id: int) -> list[dict]:
    request = _draft_or_visible_request(db, actor, request_id)
    rows = db.query(RequestAttachment).filter(
        RequestAttachment.request_id == request.id,
        RequestAttachment.status != "DELETED",
    ).order_by(RequestAttachment.created_at, RequestAttachment.id).all()
    return [_output(db, row) for row in rows if _can_read_attachment(db, actor, request, row)]


def create_pending(
    db: Session,
    actor: User,
    request_id: int,
    payload: AttachmentPresignInput,
) -> tuple[RequestAttachment, dict[str, object]]:
    request = _draft_or_visible_request(db, actor, request_id)
    if payload.mime_type not in settings.attachment_allowed_mime_types:
        raise AttachmentError(422, "This file type is not allowed")
    if payload.size_bytes > settings.attachment_max_bytes:
        raise AttachmentError(413, "Attachment exceeds the configured size limit")
    if payload.visibility == "INTERNAL" and not _can_upload_internal(db, actor, request):
        raise AttachmentError(403, "Only authorized service staff can add internal attachments")
    object_key = f"requests/{request.id}/{uuid4().hex}"
    row = RequestAttachment(
        request_id=request.id,
        uploaded_by=actor.id,
        object_key=object_key,
        original_filename=payload.filename,
        mime_type=payload.mime_type,
        size_bytes=payload.size_bytes,
        visibility=payload.visibility,
        status="PENDING",
    )
    db.add(row)
    db.flush()
    try:
        reservation = storage.presign_upload(
            object_key=object_key,
            mime_type=payload.mime_type,
            max_bytes=settings.attachment_max_bytes,
        )
    except storage.StorageError as exc:
        raise AttachmentError(503, str(exc)) from exc
    record_audit(db, "attachment_upload_reserved", actor_id=actor.id, request_id=request.id,
                 resource_type="attachment", resource_id=row.id,
                 details={"attachment_id": row.id}, domain=False)
    return row, reservation


def complete(
    db: Session,
    actor: User,
    request_id: int,
    attachment_id: int,
) -> RequestAttachment:
    request = _draft_or_visible_request(db, actor, request_id)
    row = db.query(RequestAttachment).filter_by(id=attachment_id, request_id=request.id).populate_existing().with_for_update().first()
    if row is None:
        raise AttachmentError(404, "Attachment not found")
    if row.uploaded_by != actor.id and not user_has_any_role(actor, "ADMIN"):
        raise AttachmentError(403, "Only the uploader can complete this upload")
    if row.status == "READY":
        return row
    if row.status != "PENDING":
        raise AttachmentError(409, "Attachment is not awaiting upload completion")
    try:
        head = storage.object_head(row.object_key)
    except storage.StorageError as exc:
        raise AttachmentError(409, str(exc)) from exc
    actual_size = int(head.get("ContentLength") or 0)
    actual_type = str(head.get("ContentType") or "").split(";", 1)[0].strip().lower()
    if actual_size != row.size_bytes:
        raise AttachmentError(409, "Uploaded file size does not match the reserved attachment")
    if actual_type and actual_type != row.mime_type.lower():
        raise AttachmentError(409, "Uploaded content type does not match the reserved attachment")
    row.status = "READY"
    row.ready_at = datetime.now(UTC)
    row.sha256 = None
    row.storage_etag = str(head.get("ETag") or "").strip('"') or None
    db.flush()
    record_audit(db, "attachment_ready", actor_id=actor.id, request_id=request.id,
                 resource_type="attachment", resource_id=row.id,
                 details={"attachment_id": row.id}, domain=True,
                 internal=row.visibility == "INTERNAL")
    return row


def download_url(db: Session, actor: User, request_id: int, attachment_id: int) -> str:
    request = _draft_or_visible_request(db, actor, request_id)
    row = db.query(RequestAttachment).filter_by(id=attachment_id, request_id=request.id, status="READY").first()
    if row is None or not _can_read_attachment(db, actor, request, row):
        raise AttachmentError(404, "Attachment not found")
    try:
        url = storage.presign_download(object_key=row.object_key,
                                       filename=row.original_filename,
                                       mime_type=row.mime_type)
    except storage.StorageError as exc:
        raise AttachmentError(503, str(exc)) from exc
    record_audit(db, "attachment_download_url_issued", actor_id=actor.id,
                 request_id=request.id, resource_type="attachment", resource_id=row.id,
                 details={"attachment_id": row.id}, domain=False)
    return url
