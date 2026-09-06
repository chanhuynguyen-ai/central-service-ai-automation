from typing import Any

from pydantic import BaseModel, Field


class IntakeText(BaseModel):
    text: str = Field(min_length=5, max_length=5000)


class IntakeDraftRequest(IntakeText):
    request_type_code: str | None = Field(default=None, min_length=2, max_length=80)


class IntakeAlternative(BaseModel):
    request_type_code: str
    title: str
    confidence: float = Field(ge=0.0, le=1.0)


class IntakeClarification(BaseModel):
    field: str
    prompt: str


class IntakeClassification(BaseModel):
    request_type_code: str
    title: str
    category: str
    request_type_version_id: int
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[IntakeAlternative] = Field(default_factory=list)
    needs_human_confirmation: bool
    provider: str
    model: str


class IntakeDraftSuggestion(IntakeClassification):
    extracted_fields: dict[str, Any]
    missing_required_fields: list[str]
    clarifications: list[IntakeClarification] = Field(default_factory=list)
    field_issues: list[str] = Field(default_factory=list)
