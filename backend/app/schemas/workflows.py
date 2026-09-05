from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class WorkflowCreate(StrictInput):
    code: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,79}$")
    name: str = Field(min_length=2, max_length=180)
    request_type_id: int = Field(gt=0, strict=True)


class ResolverConfig(StrictInput):
    user_id: int | None = Field(default=None, gt=0, strict=True)
    role_code: str | None = Field(default=None, pattern=r"^[A-Z][A-Z0-9_]{1,59}$")
    service_team_id: int | None = Field(default=None, gt=0, strict=True)


class StepInput(StrictInput):
    name: str = Field(min_length=2, max_length=180)
    approval_mode: Literal["ALL"] = "ALL"
    approver_resolver_type: Literal["USER", "MANAGER", "ROLE", "TEAM_LEAD"]
    approver_resolver_config: ResolverConfig = Field(default_factory=ResolverConfig)

    @model_validator(mode="after")
    def check_config(self) -> "StepInput":
        supplied = self.approver_resolver_config.model_dump(exclude_none=True)
        expected = {"USER": {"user_id"}, "MANAGER": set(), "ROLE": {"role_code"}, "TEAM_LEAD": {"service_team_id"}}[self.approver_resolver_type]
        if self.approver_resolver_type == "TEAM_LEAD" and not supplied:
            return self  # Use the catalog's owning service team, frozen on submission.
        if set(supplied) != expected:
            raise ValueError("Resolver configuration does not match its type")
        return self


class WorkflowVersionInput(StrictInput):
    approval_due_hours: int = Field(default=24, ge=1, le=720, strict=True)
    steps: list[StepInput] = Field(min_length=1, max_length=10)


class SubmitInput(StrictInput):
    revision: int = Field(gt=0, strict=True)


class DecisionInput(StrictInput):
    version: int = Field(gt=0, strict=True)
    decision: Literal["approve", "reject", "request_changes"]
    comment: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def require_reason(self) -> "DecisionInput":
        if self.decision != "approve" and not self.comment:
            raise ValueError("A reason is required for rejection or requested changes")
        return self


class WorkflowDefinitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    request_type_id: int
    is_active: bool
    created_at: datetime


class WorkflowActivationInput(StrictInput):
    is_active: bool = Field(strict=True)
