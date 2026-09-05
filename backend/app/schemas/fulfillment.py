from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class WorkItemAction(BaseModel):
    action: Literal["assign", "start", "wait", "resume", "resolve", "close"]
    version: int = Field(ge=1)
    assignee_user_id: int | None = Field(default=None, ge=1)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_action_fields(self):
        if self.action == "resolve" and not (self.note or "").strip():
            raise ValueError("A resolution summary is required")
        if self.action != "assign" and self.assignee_user_id is not None:
            raise ValueError("assignee_user_id is only valid for assign")
        return self


class WorkItemOut(BaseModel):
    id: int
    request_id: int
    reference: str
    title: str
    requester_name: str
    service_team_id: int
    service_team_name: str
    assignee_user_id: int | None
    assignee_name: str | None
    status: str
    version: int
    resolution_summary: str | None
    queued_at: datetime
    assigned_at: datetime | None
    started_at: datetime | None
    waiting_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    due_at: datetime | None
    can_manage: bool
