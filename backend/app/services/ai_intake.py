import json
import re
from dataclasses import dataclass
from time import perf_counter

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.catalog import RequestType, RequestTypeVersion
from app.models.models import AutomationRun
from app.schemas.ai_intake import (
    IntakeAlternative,
    IntakeClassification,
    IntakeDraftSuggestion,
)
from app.schemas.catalog import DynamicFormSchema
from app.services.form_validation import validate_form_data
from app.services.llm import LLMClient, extract_json

TOKEN = re.compile(r"[a-z0-9]+")


@dataclass
class CatalogCandidate:
    request_type: RequestType
    version: RequestTypeVersion
    score: float


class ModelIntakePayload(BaseModel):
    request_type_code: str = Field(min_length=2, max_length=80)
    confidence: float = Field(ge=0.0, le=1.0)
    alternatives: list[str] = Field(default_factory=list, max_length=3)
    fields: dict = Field(default_factory=dict)


def _tokens(text: str) -> set[str]:
    return set(TOKEN.findall(text.lower()))


def _published_catalog(db: Session) -> list[tuple[RequestType, RequestTypeVersion]]:
    return (
        db.query(RequestType, RequestTypeVersion)
        .join(RequestTypeVersion, RequestTypeVersion.request_type_id == RequestType.id)
        .filter(RequestType.is_active.is_(True), RequestTypeVersion.status == "PUBLISHED")
        .order_by(RequestType.code.asc())
        .all()
    )


def _rank(text: str, rows: list[tuple[RequestType, RequestTypeVersion]]) -> list[CatalogCandidate]:
    query = _tokens(text)
    ranked: list[CatalogCandidate] = []
    for request_type, version in rows:
        haystack = _tokens(
            " ".join(
                [
                    request_type.code.replace("_", " "),
                    request_type.category,
                    version.title,
                    version.description or "",
                ]
            )
        )
        overlap = len(query & haystack)
        phrase_bonus = 2 if version.title.lower() in text.lower() else 0
        score = float(overlap + phrase_bonus)
        ranked.append(CatalogCandidate(request_type, version, score))
    return sorted(ranked, key=lambda item: (-item.score, item.request_type.code))


def _confidence(ranked: list[CatalogCandidate]) -> float:
    if not ranked or ranked[0].score <= 0:
        return 0.25
    best = ranked[0].score
    second = ranked[1].score if len(ranked) > 1 else 0.0
    margin = max(0.0, best - second)
    return min(0.96, 0.55 + min(best, 4.0) * 0.08 + min(margin, 2.0) * 0.08)


def _alternatives(ranked: list[CatalogCandidate], selected_code: str) -> list[IntakeAlternative]:
    alternatives: list[IntakeAlternative] = []
    for item in ranked:
        if item.request_type.code == selected_code:
            continue
        alternatives.append(
            IntakeAlternative(
                request_type_code=item.request_type.code,
                title=item.version.title,
                confidence=max(0.1, min(0.75, 0.25 + item.score * 0.1)),
            )
        )
        if len(alternatives) == 2:
            break
    return alternatives


def _mock_extract(text: str, schema: DynamicFormSchema) -> dict:
    lowered = text.lower()
    extracted: dict = {}
    for section in schema.sections:
        for field in section.fields:
            if field.type == "select":
                for option in field.options:
                    if option.value.lower() in lowered or option.label.lower() in lowered:
                        extracted[field.key] = option.value
                        break
            elif field.type == "boolean":
                label = field.label.lower()
                if label in lowered:
                    if any(word in lowered for word in {"yes", "true", "required", "needed"}):
                        extracted[field.key] = True
                    elif any(word in lowered for word in {"no", "false", "not required", "not needed"}):
                        extracted[field.key] = False
            elif field.type in {"text", "textarea"}:
                key_terms = _tokens(field.key.replace("_", " ") + " " + field.label)
                if key_terms & _tokens(text):
                    extracted[field.key] = text[:5000 if field.type == "textarea" else 500]
    return extracted


def _model_payload(
    client: LLMClient,
    text: str,
    rows: list[tuple[RequestType, RequestTypeVersion]],
    selected: RequestTypeVersion | None = None,
) -> ModelIntakePayload:
    catalog = [
        {
            "code": request_type.code,
            "category": request_type.category,
            "title": version.title,
            "description": version.description,
        }
        for request_type, version in rows
    ]
    schema = selected.form_schema if selected is not None else None
    raw = client.complete(
        "You convert employee needs into structured service-request suggestions. Return strict JSON only. "
        "Never invent employee identity, policy, approvers, dates, IDs or facts not present in the user text. "
        "Choose only request type codes and field keys/options supplied in the prompt.",
        json.dumps(
            {
                "task": "classify_and_extract" if selected is not None else "classify",
                "user_text": text,
                "allowed_catalog": catalog,
                "selected_form_schema": schema,
                "output": {
                    "request_type_code": "one allowed code",
                    "confidence": "number 0..1",
                    "alternatives": ["up to 3 allowed codes"],
                    "fields": "object using only supplied form keys; omit unknown values",
                },
            },
            ensure_ascii=False,
        ),
    )
    return ModelIntakePayload.model_validate(extract_json(raw))


class AIIntakeService:
    def __init__(self) -> None:
        self.client = LLMClient()

    def classify(self, db: Session, text: str) -> IntakeClassification:
        start = perf_counter()
        rows = _published_catalog(db)
        if not rows:
            raise LookupError("No published request types are available")
        ranked = _rank(text, rows)
        provider = settings.llm_provider
        model = settings.llm_model if provider != "mock" else "catalog-ranker-v1"
        selected = ranked[0]
        confidence = _confidence(ranked)
        alternatives = _alternatives(ranked, selected.request_type.code)

        if provider != "mock":
            try:
                payload = _model_payload(self.client, text, rows)
                allowed = {request_type.code: (request_type, version) for request_type, version in rows}
                if payload.request_type_code not in allowed:
                    raise ValueError("Model selected an unpublished request type")
                request_type, version = allowed[payload.request_type_code]
                selected = CatalogCandidate(request_type, version, 0.0)
                confidence = payload.confidence
                ranked_codes = [code for code in payload.alternatives if code in allowed]
                alternatives = [
                    IntakeAlternative(
                        request_type_code=code,
                        title=allowed[code][1].title,
                        confidence=max(0.1, min(0.75, confidence - 0.15 - index * 0.1)),
                    )
                    for index, code in enumerate(ranked_codes[:2])
                    if code != payload.request_type_code
                ]
            except (httpx.HTTPError, KeyError, ValueError, TypeError, ValidationError, json.JSONDecodeError):
                provider = f"{provider}:fallback"
                model = "catalog-ranker-v1"

        latency_ms = int((perf_counter() - start) * 1000)
        db.add(
            AutomationRun(
                workflow_name="ai_intake_classify",
                status="success",
                duration_ms=latency_ms,
                provider=provider,
            )
        )
        return IntakeClassification(
            request_type_code=selected.request_type.code,
            title=selected.version.title,
            category=selected.request_type.category,
            request_type_version_id=selected.version.id,
            confidence=confidence,
            alternatives=alternatives,
            needs_human_confirmation=confidence < 0.8,
            provider=provider,
            model=model,
        )

    def draft(self, db: Session, text: str, request_type_code: str | None = None) -> IntakeDraftSuggestion:
        rows = _published_catalog(db)
        if not rows:
            raise LookupError("No published request types are available")
        by_code = {request_type.code: (request_type, version) for request_type, version in rows}
        classification = self.classify(db, text)
        selected_code = request_type_code or classification.request_type_code
        if selected_code not in by_code:
            raise LookupError("Published request type not found")
        request_type, version = by_code[selected_code]
        schema = DynamicFormSchema.model_validate(version.form_schema)

        provider = classification.provider
        model = classification.model
        extracted = _mock_extract(text, schema)
        if settings.llm_provider != "mock":
            try:
                payload = _model_payload(self.client, text, rows, version)
                extracted = payload.fields
                provider = settings.llm_provider
                model = settings.llm_model
            except (httpx.HTTPError, KeyError, ValueError, TypeError, ValidationError, json.JSONDecodeError):
                provider = f"{settings.llm_provider}:fallback"
                model = "catalog-ranker-v1"

        cleaned, issues = validate_form_data(schema, extracted, require_complete=False, db=db)
        fields = {field.key: field for section in schema.sections for field in section.fields}
        missing = [key for key, field in fields.items() if field.required and key not in cleaned]
        issue_codes = [f"{issue.field}:{issue.code}" for issue in issues]
        confidence = classification.confidence if selected_code == classification.request_type_code else 1.0
        alternatives = classification.alternatives if request_type_code is None else []
        db.add(
            AutomationRun(
                workflow_name="ai_intake_extract",
                status="success",
                duration_ms=0,
                provider=provider,
            )
        )
        return IntakeDraftSuggestion(
            request_type_code=request_type.code,
            title=version.title,
            category=request_type.category,
            request_type_version_id=version.id,
            confidence=confidence,
            alternatives=alternatives,
            needs_human_confirmation=True,
            provider=provider,
            model=model,
            extracted_fields=cleaned,
            missing_required_fields=missing,
            field_issues=issue_codes,
        )


ai_intake_service = AIIntakeService()
