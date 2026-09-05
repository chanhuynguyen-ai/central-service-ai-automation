"""Request attachment metadata; binary content lives in S3-compatible storage."""
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.models import utcnow


class RequestAttachment(Base):
    __tablename__ = "request_attachments"
    __table_args__ = (
        CheckConstraint(
            "status IN ('PENDING','READY','QUARANTINED','DELETED')",
            name="ck_request_attachment_status",
        ),
        CheckConstraint(
            "visibility IN ('REQUESTER_VISIBLE','INTERNAL')",
            name="ck_request_attachment_visibility",
        ),
        Index("ix_request_attachments_request_status", "request_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    object_key: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(160), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    visibility: Mapped[str] = mapped_column(String(24), default="REQUESTER_VISIBLE")
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    storage_etag: Mapped[str | None] = mapped_column(Text, nullable=True)
