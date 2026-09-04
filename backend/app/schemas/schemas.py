from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshTokenInput(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class LogoutInput(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=512)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    department: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RequestCreate(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=5000)
    category: str | None = Field(default=None, max_length=60)
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")


class RequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    department: str
    assigned_to: str | None
    ai_summary: str | None
    ai_category: str | None
    ai_priority: str | None
    ai_confidence: float | None
    ai_model: str | None
    requester: UserOut
    submitted_at: datetime
    due_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class RequestList(BaseModel):
    items: list[RequestOut]
    total: int


class DecisionInput(BaseModel):
    decision: str = Field(pattern="^(approve|reject)$")
    comment: str = Field(default="", max_length=2000)


class StatusUpdate(BaseModel):
    status: str = Field(pattern="^(in_progress|completed|cancelled)$")
    comment: str = Field(default="", max_length=2000)


class CitationOut(BaseModel):
    article_id: int
    title: str
    version: str
    score: float


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    request_reference: str | None = Field(default=None, max_length=30)


class AssistantAnswer(BaseModel):
    answer: str
    citations: list[CitationOut]
    provider: str
    model: str
    grounded: bool
    latency_ms: int


class CategoryMetric(BaseModel):
    category: str
    count: int


class AnalyticsSummary(BaseModel):
    total_requests: int
    open_requests: int
    pending_approvals: int
    completed_requests: int
    sla_compliance_rate: float
    automation_success_rate: float
    ai_triage_coverage: float
    category_breakdown: list[CategoryMetric]


class AutomationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int | None
    workflow_name: str
    status: str
    duration_ms: int
    provider: str
    error: str | None
    created_at: datetime


class HealthOut(BaseModel):
    status: str
    database: str
    llm_provider: str
    version: str


class ReadinessOut(BaseModel):
    status: str
    database: str
    version: str


class PowerPlatformIntake(BaseModel):
    requester_email: EmailStr
    title: str = Field(min_length=5, max_length=180)
    description: str = Field(min_length=15, max_length=5000)
    category: str | None = Field(default=None, max_length=60)
    priority: str | None = Field(default=None, pattern="^(low|medium|high|urgent)$")
    source_record_id: str | None = Field(default=None, max_length=120)


class PowerPlatformDecision(BaseModel):
    approver_email: EmailStr
    decision: str = Field(pattern="^(approve|reject)$")
    comment: str = Field(default="", max_length=2000)


class AnalyticsFeedRow(BaseModel):
    reference: str
    title: str
    department: str
    category: str
    priority: str
    status: str
    submitted_at: datetime
    due_at: datetime
    completed_at: datetime | None
    ai_confidence: float | None
    within_sla: bool
