"""Append-only domain history, deliberately separate from operational audit."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column, object_session

from app.core.logging import request_id_context
from app.db.session import Base
from app.models.models import AuditEvent, UserRole, utcnow


class RequestEvent(Base):
    __tablename__ = "request_events"
    __table_args__ = (
        CheckConstraint("visibility IN ('REQUESTER_VISIBLE', 'INTERNAL')", name="ck_event_visibility"),
        Index("ix_request_events_request_id_id", "request_id", "id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(60))
    visibility: Mapped[str] = mapped_column(String(30), default="REQUESTER_VISIBLE")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    source_audit_id: Mapped[int | None] = mapped_column(ForeignKey("audit_events.id"), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RequestComment(Base):
    __tablename__ = "request_comments"
    __table_args__ = (
        CheckConstraint("visibility IN ('REQUESTER_VISIBLE', 'INTERNAL')", name="ck_comment_visibility"),
        UniqueConstraint("request_id", "author_user_id", "client_token", name="uq_comment_idempotency"),
        Index("ix_request_comments_request_id_id", "request_id", "id"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id"))
    author_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(String(30))
    client_token: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


def _immutable(_mapper, _connection, _target):
    raise ValueError("History is append-only; record a new event or comment instead.")


# These guards also protect ORM fixtures. Migrations install database triggers
# for raw SQL UPDATE/DELETE (and PostgreSQL TRUNCATE), which ORM hooks cannot stop.
for _model in (RequestEvent, RequestComment, AuditEvent):
    event.listen(_model, "before_update", _immutable)
    event.listen(_model, "before_delete", _immutable)


def _role_audit(_mapper, connection, target, action):
    # Mapper hooks capture existing ORM/seed role assignments. Direct SQL by a
    # database administrator is outside the application audit boundary.
    session = object_session(target)
    actor_id = session.info.get("audit_actor_id") if session else None
    try:
        correlation = str(UUID(request_id_context.get()))
    except (ValueError, TypeError, AttributeError):
        correlation = None
    connection.execute(AuditEvent.__table__.insert().values(
        actor_id=actor_id, event_type=action, resource_type="user", resource_id=str(target.user_id),
        correlation_id=correlation, details={"user_id": target.user_id, "role_id": target.role_id},
    ))


def _role_added(mapper, connection, target):
    _role_audit(mapper, connection, target, "role_assigned")


def _role_removed(mapper, connection, target):
    _role_audit(mapper, connection, target, "role_removed")



event.listen(UserRole, "after_insert", _role_added)
event.listen(UserRole, "after_delete", _role_removed)
