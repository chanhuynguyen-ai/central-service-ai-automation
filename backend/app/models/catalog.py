from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class RequestType(Base):
    __tablename__ = "request_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(80), index=True)
    owner_service_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("service_teams.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    versions: Mapped[list["RequestTypeVersion"]] = relationship(
        back_populates="request_type", cascade="all, delete-orphan",
        order_by="RequestTypeVersion.version",
    )


class RequestTypeVersion(Base):
    __tablename__ = "request_type_versions"
    __table_args__ = (
        UniqueConstraint("request_type_id", "version", name="uq_request_type_version"),
        Index("uq_request_type_one_published", "request_type_id", unique=True,
              sqlite_where=text("status = 'PUBLISHED'"),
              postgresql_where=text("status = 'PUBLISHED'")),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    request_type_id: Mapped[int] = mapped_column(
        ForeignKey("request_types.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    form_schema: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sla_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    attachment_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    request_type: Mapped[RequestType] = relationship(back_populates="versions")
