from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from app.schemas.catalog import RequestTypeVersionOut


class DraftValues(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(default="", max_length=180)
    description: str = Field(default="", max_length=5000)
    form_data: dict[str, JsonValue] = Field(default_factory=dict, max_length=100)


class DraftCreate(DraftValues):
    request_type_version_id: int = Field(gt=0, strict=True)


class DraftUpdate(DraftValues):
    revision: int = Field(gt=0, strict=True)


class FieldIssue(BaseModel):
    field: str
    code: str
    message: str


class DraftValidation(BaseModel):
    valid: bool
    errors: list[FieldIssue]
    missing_fields: list[str]


class DraftOut(BaseModel):
    id: int
    reference: str
    title: str
    description: str
    status: Literal["draft", "changes_requested"] = "draft"
    request_type_version_id: int
    revision: int
    form_data: dict[str, JsonValue]
    updated_at: datetime
    request_type_version: RequestTypeVersionOut
    validation: DraftValidation


class DraftList(BaseModel):
    items: list[DraftOut]
    total: int
