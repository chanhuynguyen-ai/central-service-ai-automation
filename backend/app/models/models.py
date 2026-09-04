from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="department_ref",
        foreign_keys="User.department_id",
    )
    service_teams: Mapped[list["ServiceTeam"]] = relationship(
        back_populates="department",
    )


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    user_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="role",
        cascade="all, delete-orphan",
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))

    # Legacy compatibility fields.
    #
    # These remain temporarily while the application migrates from the
    # prototype single-role/string-department model to normalized
    # organization and RBAC relationships.
    department: Mapped[str] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(
        String(30),
        default="employee",
        index=True,
    )

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    manager_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    department_ref: Mapped[Department | None] = relationship(
        back_populates="users",
        foreign_keys=[department_id],
    )

    manager: Mapped["User | None"] = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[manager_id],
        back_populates="direct_reports",
    )
    direct_reports: Mapped[list["User"]] = relationship(
        "User",
        foreign_keys="User.manager_id",
        back_populates="manager",
    )

    role_assignments: Mapped[list["UserRole"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    service_team_memberships: Mapped[list["ServiceTeamMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    led_service_teams: Mapped[list["ServiceTeam"]] = relationship(
        back_populates="lead",
        foreign_keys="ServiceTeam.lead_user_id",
    )

    requests: Mapped[list["ServiceRequest"]] = relationship(
        back_populates="requester",
    )


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[int] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    user: Mapped[User] = relationship(
        back_populates="role_assignments",
    )
    role: Mapped[Role] = relationship(
        back_populates="user_assignments",
    )


class ServiceTeam(Base):
    __tablename__ = "service_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))

    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    lead_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    department: Mapped[Department | None] = relationship(
        back_populates="service_teams",
    )
    lead: Mapped[User | None] = relationship(
        back_populates="led_service_teams",
        foreign_keys=[lead_user_id],
    )
    memberships: Mapped[list["ServiceTeamMember"]] = relationship(
        back_populates="service_team",
        cascade="all, delete-orphan",
    )


class ServiceTeamMember(Base):
    __tablename__ = "service_team_members"

    service_team_id: Mapped[int] = mapped_column(
        ForeignKey("service_teams.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    service_team: Mapped[ServiceTeam] = relationship(
        back_populates="memberships",
    )
    user: Mapped[User] = relationship(
        back_populates="service_team_memberships",
    )


class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(180), index=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(60), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(
        String(30),
        default="pending_approval",
        index=True,
    )
    department: Mapped[str] = mapped_column(String(80), index=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(120),
        nullable=True,
    )

    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_category: Mapped[str | None] = mapped_column(
        String(60),
        nullable=True,
    )
    ai_priority: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    ai_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    ai_model: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    requester: Mapped[User] = relationship(
        back_populates="requests",
    )
    approvals: Mapped[list["Approval"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )
    audit_events: Mapped[list["AuditEvent"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )


class Approval(Base):
    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int] = mapped_column(
        ForeignKey("service_requests.id"),
        index=True,
    )
    approver_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        index=True,
    )
    decision: Mapped[str] = mapped_column(String(20))
    comment: Mapped[str] = mapped_column(Text, default="")
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    request: Mapped[ServiceRequest] = relationship(
        back_populates="approvals",
    )
    approver: Mapped[User] = relationship()


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_requests.id"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(
        String(60),
        index=True,
    )
    details: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )

    request: Mapped[ServiceRequest | None] = relationship(
        back_populates="audit_events",
    )


class AutomationRun(Base):
    __tablename__ = "automation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_requests.id"),
        nullable=True,
        index=True,
    )
    workflow_name: Mapped[str] = mapped_column(
        String(80),
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        index=True,
    )
    duration_ms: Mapped[int] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(80))
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )


class KnowledgeArticle(Base):
    __tablename__ = "knowledge_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(180))
    content: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(
        String(20),
        default="1.0",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )
    metadata_json: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utcnow,
    )