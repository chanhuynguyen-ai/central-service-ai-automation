from app.db.seed_catalog import seed_catalog
from app.models.attachments import RequestAttachment
from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AuditEvent, ServiceRequest, User
from app.schemas.attachments import AttachmentPresignInput
from app.services import attachments


def _user(db, email: str) -> User:
    return db.query(User).filter_by(email=email).one()


def _structured_request(db, *, status="approved") -> ServiceRequest:
    seed_catalog(db)
    requester = _user(db, "employee@centralops.demo")
    version = db.query(RequestTypeVersion).join(RequestType).filter(
        RequestType.code == "IT_LAPTOP_REPLACEMENT",
        RequestTypeVersion.status == "PUBLISHED",
    ).one()
    row = ServiceRequest(
        reference=f"ATT-{db.query(ServiceRequest).count() + 1}",
        title="Attachment test",
        description="Structured request with evidence",
        category="IT",
        priority="medium",
        status=status,
        department=requester.department,
        requester_id=requester.id,
        request_type_version_id=version.id,
        form_data={},
        approval_state="approved" if status == "approved" else None,
        fulfillment_state="not_queued" if status == "approved" else None,
        submitted_at=None if status == "draft" else version.created_at,
    )
    db.add(row)
    db.flush()
    return row


def test_requester_reserves_completes_and_downloads_ready_attachment(db_session, monkeypatch):
    db = db_session
    request = _structured_request(db)
    requester = _user(db, "employee@centralops.demo")
    monkeypatch.setattr(attachments.storage, "presign_upload", lambda **_: "http://storage/upload")
    monkeypatch.setattr(
        attachments.storage,
        "object_head",
        lambda _key: {"ContentLength": 12, "ContentType": "application/pdf", "ETag": '"abc"'},
    )
    monkeypatch.setattr(attachments.storage, "presign_download", lambda **_: "http://storage/download")

    row, url = attachments.create_pending(
        db,
        requester,
        request.id,
        AttachmentPresignInput(
            filename="evidence.pdf",
            mime_type="application/pdf",
            size_bytes=12,
        ),
    )
    assert url == "http://storage/upload"
    assert row.status == "PENDING"
    ready = attachments.complete(db, requester, request.id, row.id, "a" * 64)
    assert ready.status == "READY"
    assert ready.storage_etag == "abc"
    assert attachments.download_url(db, requester, request.id, row.id) == "http://storage/download"
    assert db.query(AuditEvent).filter_by(event_type="attachment_ready", request_id=request.id).count() == 1


def test_completion_rejects_object_size_mismatch(db_session, monkeypatch):
    db = db_session
    request = _structured_request(db)
    requester = _user(db, "employee@centralops.demo")
    monkeypatch.setattr(attachments.storage, "presign_upload", lambda **_: "http://storage/upload")
    monkeypatch.setattr(
        attachments.storage,
        "object_head",
        lambda _key: {"ContentLength": 99, "ContentType": "application/pdf"},
    )
    row, _ = attachments.create_pending(
        db, requester, request.id,
        AttachmentPresignInput(filename="evidence.pdf", mime_type="application/pdf", size_bytes=12),
    )
    try:
        attachments.complete(db, requester, request.id, row.id, None)
        raise AssertionError("size mismatch must fail")
    except attachments.AttachmentError as exc:
        assert exc.status_code == 409
    assert db.get(RequestAttachment, row.id).status == "PENDING"


def test_requester_cannot_create_or_read_internal_attachment(db_session, monkeypatch):
    db = db_session
    request = _structured_request(db)
    requester = _user(db, "employee@centralops.demo")
    monkeypatch.setattr(attachments.storage, "presign_upload", lambda **_: "http://storage/upload")

    try:
        attachments.create_pending(
            db, requester, request.id,
            AttachmentPresignInput(
                filename="internal.pdf", mime_type="application/pdf", size_bytes=12,
                visibility="INTERNAL",
            ),
        )
        raise AssertionError("requester internal upload must fail")
    except attachments.AttachmentError as exc:
        assert exc.status_code == 403

    admin = _user(db, "admin@centralops.demo")
    row, _ = attachments.create_pending(
        db, admin, request.id,
        AttachmentPresignInput(
            filename="internal.pdf", mime_type="application/pdf", size_bytes=12,
            visibility="INTERNAL",
        ),
    )
    row.status = "READY"
    db.flush()
    assert all(item["id"] != row.id for item in attachments.list_attachments(db, requester, request.id))
    assert any(item["id"] == row.id for item in attachments.list_attachments(db, admin, request.id))


def test_other_employee_cannot_access_request_attachments(db_session):
    db = db_session
    request = _structured_request(db)
    other = _user(db, "other.employee@centralops.demo")
    try:
        attachments.list_attachments(db, other, request.id)
        raise AssertionError("unrelated employee must not see attachments")
    except attachments.AttachmentError as exc:
        assert exc.status_code == 404


def test_draft_attachment_access_is_owner_only(db_session, monkeypatch):
    db = db_session
    request = _structured_request(db, status="draft")
    requester = _user(db, "employee@centralops.demo")
    other = _user(db, "other.employee@centralops.demo")
    monkeypatch.setattr(attachments.storage, "presign_upload", lambda **_: "http://storage/upload")
    row, _ = attachments.create_pending(
        db, requester, request.id,
        AttachmentPresignInput(filename="draft.txt", mime_type="text/plain", size_bytes=4),
    )
    assert row.request_id == request.id
    try:
        attachments.list_attachments(db, other, request.id)
        raise AssertionError("draft must remain owner-only")
    except attachments.AttachmentError as exc:
        assert exc.status_code == 404
