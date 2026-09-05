"""Operational service fulfillment work items (M5)."""
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.models import utcnow


class ServiceWorkItem(Base):
    __tablename__ = "service_work_items"
    __table_args__ = (
        UniqueConstraint("request_id", name="uq_service_work_item_request"),
        CheckConstraint(
            "status IN ('QUEUED','ASSIGNED','IN_PROGRESS','WAITING_REQUESTER','RESOLVED','CLOSED')",
            name="ck_service_work_item_status",
        ),
        Index("ix_service_work_items_team_status", "service_team_id", "status"),
        Index("ix_service_work_items_assignee_status", "assignee_user_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("service_requests.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    service_team_id: Mapped[int] = mapped_column(
        ForeignKey("service_teams.id", ondelete="RESTRICT"), nullable=False, index=True,
    )
    assignee_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(String(30), default="QUEUED", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    resolution_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    waiting_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
