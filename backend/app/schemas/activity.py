from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Visibility = Literal["REQUESTER_VISIBLE", "INTERNAL"]


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)
    visibility: Visibility = "REQUESTER_VISIBLE"
    client_token: UUID

    @field_validator("body")
    @classmethod
    def nonblank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("A comment cannot be blank")
        if any(ord(char) < 32 and char not in "\n\r\t" for char in value):
            raise ValueError("Control characters are not allowed")
        return value


class CommentOut(BaseModel):
    id: int
    request_id: int
    author_user_id: int
    author_name: str
    body: str
    visibility: Visibility
    created_at: datetime


class EventOut(BaseModel):
    id: int
    request_id: int
    actor_id: int | None
    actor_name: str | None
    event_type: str
    visibility: Visibility
    payload: dict
    created_at: datetime


class ActivityPermissions(BaseModel):
    can_comment: bool
    can_read_internal: bool
    can_write_internal: bool


class CommentPage(BaseModel):
    items: list[CommentOut]
    next_before_id: int | None


class EventPage(BaseModel):
    items: list[EventOut]
    next_before_id: int | None


class AuditOut(BaseModel):
    id: int
    actor_id: int | None
    actor_name: str | None
    request_id: int | None
    event_type: str
    resource_type: str | None
    resource_id: str | None
    correlation_id: str | None
    details: dict
    created_at: datetime


class AuditPage(BaseModel):
    items: list[AuditOut]
    next_before_id: int | None
