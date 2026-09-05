"""Versioned definitions and append-only approval attempts (M3)."""
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.models import utcnow


class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(180))
    request_type_id: Mapped[int] = mapped_column(ForeignKey("request_types.id", ondelete="RESTRICT"), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WorkflowVersion(Base):
    __tablename__ = "workflow_versions"
    __table_args__ = (
        UniqueConstraint("workflow_definition_id", "version", name="uq_workflow_version"),
        Index("uq_workflow_published", "workflow_definition_id", unique=True,
              postgresql_where=text("status = 'PUBLISHED'"), sqlite_where=text("status = 'PUBLISHED'")),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_definition_id: Mapped[int] = mapped_column(ForeignKey("workflow_definitions.id", ondelete="RESTRICT"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="DRAFT")
    approval_due_hours: Mapped[int] = mapped_column(Integer, default=24)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowStepDefinition(Base):
    __tablename__ = "workflow_step_definitions"
    __table_args__ = (UniqueConstraint("workflow_version_id", "step_order", name="uq_workflow_step_order"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_version_id: Mapped[int] = mapped_column(ForeignKey("workflow_versions.id", ondelete="RESTRICT"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(180))
    approval_mode: Mapped[str] = mapped_column(String(10), default="ALL")
    approver_resolver_type: Mapped[str] = mapped_column(String(20))
    approver_resolver_config: Mapped[dict] = mapped_column(JSON, default=dict)


class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    __table_args__ = (
        UniqueConstraint("request_id", "attempt", name="uq_workflow_attempt"),
        Index("uq_workflow_active_request", "request_id", unique=True,
              postgresql_where=text("status = 'PENDING'"), sqlite_where=text("status = 'PENDING'")),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("service_requests.id", ondelete="RESTRICT"), index=True)
    workflow_version_id: Mapped[int] = mapped_column(ForeignKey("workflow_versions.id", ondelete="RESTRICT"))
    attempt: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    snapshot: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkflowStepInstance(Base):
    __tablename__ = "workflow_step_instances"
    __table_args__ = (UniqueConstraint("workflow_instance_id", "step_order", name="uq_workflow_runtime_step"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_instance_id: Mapped[int] = mapped_column(ForeignKey("workflow_instances.id", ondelete="RESTRICT"), index=True)
    step_order: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(180))
    status: Mapped[str] = mapped_column(String(24), default="PENDING")
    approver_ids: Mapped[list] = mapped_column(JSON)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalTask(Base):
    __tablename__ = "approval_tasks"
    __table_args__ = (UniqueConstraint("workflow_step_instance_id", "approver_user_id", name="uq_approval_task_assignee"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    workflow_step_instance_id: Mapped[int] = mapped_column(ForeignKey("workflow_step_instances.id", ondelete="RESTRICT"), index=True)
    approver_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    status: Mapped[str] = mapped_column(String(24), default="PENDING", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_task_id: Mapped[int] = mapped_column(ForeignKey("approval_tasks.id", ondelete="RESTRICT"), unique=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    decision: Mapped[str] = mapped_column(String(24))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
