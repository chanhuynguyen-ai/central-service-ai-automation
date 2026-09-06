from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PolicyDocumentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=2, max_length=120, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    title: str = Field(min_length=3, max_length=220)
    version: str = Field(min_length=1, max_length=40)
    content: str = Field(min_length=20, max_length=200_000)
    source_name: str | None = Field(default=None, max_length=255)
    status: str = Field(default="PUBLISHED", pattern=r"^(DRAFT|PUBLISHED|RETIRED)$")
    access_scope: str = Field(default="ALL", pattern=r"^(ALL|DEPARTMENT|ROLE)$")
    department_id: int | None = Field(default=None, gt=0)
    role_code: str | None = Field(default=None, min_length=2, max_length=60)
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def validate_scope_and_dates(self) -> "PolicyDocumentCreate":
        if self.access_scope == "DEPARTMENT" and self.department_id is None:
            raise ValueError("department_id is required for DEPARTMENT scope")
        if self.access_scope != "DEPARTMENT" and self.department_id is not None:
            raise ValueError("department_id is only valid for DEPARTMENT scope")
        if self.access_scope == "ROLE" and not self.role_code:
            raise ValueError("role_code is required for ROLE scope")
        if self.access_scope != "ROLE" and self.role_code is not None:
            raise ValueError("role_code is only valid for ROLE scope")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be earlier than effective_from")
        return self


class PolicyDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    version: str
    source_name: str | None
    status: str
    is_active: bool
    access_scope: str
    department_id: int | None
    role_code: str | None
    effective_from: datetime | None
    effective_to: datetime | None
    checksum_sha256: str
    created_by: int | None
    created_at: datetime
    chunk_count: int


class PolicyQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=5, max_length=3000)
    top_k: int = Field(default=4, ge=1, le=8)


class PolicyCitation(BaseModel):
    document_id: int
    chunk_id: int
    title: str
    version: str
    source_name: str | None
    page: int | None
    section: str | None
    score: float = Field(ge=-1.0, le=1.0)


class PolicyAnswer(BaseModel):
    answer: str
    grounded: bool
    insufficient_evidence: bool
    citations: list[PolicyCitation]
    provider: str
    model: str
    latency_ms: int
