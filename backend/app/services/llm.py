import json
import re
from dataclasses import dataclass
from typing import Literal
from time import perf_counter

import httpx
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AutomationRun
from app.services.retrieval import RetrievedArticle, retrieve_articles


@dataclass
class TriageResult:
    category: str
    priority: str
    summary: str
    confidence: float
    provider: str
    model: str
    latency_ms: int


@dataclass
class AssistantResult:
    answer: str
    citations: list[RetrievedArticle]
    provider: str
    model: str
    latency_ms: int


CATEGORY_RULES = {
    "access_request": {"access", "permission", "vpn", "account", "login", "password"},
    "it_support": {"laptop", "computer", "software", "scanner", "printer", "network", "email"},
    "hr_support": {"payroll", "leave", "benefit", "employee", "contract", "onboarding"},
    "facility": {"air", "meeting room", "light", "office", "building", "desk"},
    "procurement": {"purchase", "buy", "vendor", "quotation", "headset", "equipment"},
}


def heuristic_triage(title: str, description: str) -> tuple[str, str, str, float]:
    combined = f"{title} {description}".lower()
    category = "general_service"
    best_matches = 0
    for candidate, keywords in CATEGORY_RULES.items():
        matches = sum(keyword in combined for keyword in keywords)
        if matches > best_matches:
            category, best_matches = candidate, matches

    urgent_terms = {"critical", "security", "outage", "blocked", "urgent", "production down"}
    high_terms = {"cannot work", "deadline", "new starter", "broken", "customer impact"}
    if any(term in combined for term in urgent_terms):
        priority = "urgent"
    elif any(term in combined for term in high_terms):
        priority = "high"
    else:
        priority = "medium"

    summary = f"{title.strip()}. " + description.strip().split(".")[0][:220]
    confidence = min(0.96, 0.72 + best_matches * 0.08)
    return category, priority, summary, confidence


class LLMClient:
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        if settings.llm_provider == "ollama":
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/api/chat",
                json={
                    "model": settings.llm_model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]

        if settings.llm_provider == "openai_compatible":
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "temperature": 0.1,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                },
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]

        raise RuntimeError("External completion requested while LLM_PROVIDER=mock")


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("LLM response did not contain a JSON object")
    return json.loads(match.group(0))


class TriagePayload(BaseModel):
    category: Literal[
        "access_request",
        "it_support",
        "hr_support",
        "facility",
        "procurement",
        "general_service",
    ]
    priority: Literal["low", "medium", "high", "urgent"]
    summary: str = Field(min_length=3, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)


def parse_triage_payload(text: str) -> TriagePayload:
    return TriagePayload.model_validate(extract_json(text))


class AIService:
    def __init__(self) -> None:
        self.client = LLMClient()

    def triage(self, db: Session, title: str, description: str) -> TriageResult:
        start = perf_counter()
        provider = settings.llm_provider
        model = settings.llm_model if provider != "mock" else "deterministic-fallback-v1"
        fallback = heuristic_triage(title, description)

        if provider == "mock":
            category, priority, summary, confidence = fallback
        else:
            try:
                raw = self.client.complete(
                    "You classify internal employee service requests. Return strict JSON only.",
                    f"""Classify the request into one category: access_request, it_support,
hr_support, facility, procurement, general_service. Choose priority from low, medium,
high, urgent. Summarize in one sentence. Return keys category, priority, summary,
confidence (0 to 1).\nTitle: {title}\nDescription: {description}""",
                )
                parsed = parse_triage_payload(raw)
                category = parsed.category
                priority = parsed.priority
                summary = parsed.summary
                confidence = parsed.confidence
            except (
                httpx.HTTPError,
                KeyError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
                ValidationError,
            ):
                category, priority, summary, confidence = fallback
                provider = f"{provider}:fallback"
                model = "deterministic-fallback-v1"

        latency_ms = int((perf_counter() - start) * 1000)
        db.add(
            AutomationRun(
                workflow_name="ai_triage",
                status="success",
                duration_ms=latency_ms,
                provider=provider,
            )
        )
        return TriageResult(category, priority, summary, confidence, provider, model, latency_ms)

    def answer(self, db: Session, question: str, request_context: str = "") -> AssistantResult:
        start = perf_counter()
        citations = retrieve_articles(db, question)
        context = "\n\n".join(
            f"[{item.article.title} v{item.article.version}]\n{item.article.content}"
            for item in citations
        )
        provider = settings.llm_provider
        model = settings.llm_model if provider != "mock" else "grounded-template-v1"

        if provider == "mock":
            if citations:
                source = citations[0].article
                answer = (
                    f"Based on {source.title}, {source.content[:430].strip()} "
                    "If the situation is exceptional, ask the service owner to confirm the route."
                )
            else:
                answer = (
                    "I could not find supporting policy content. Please contact the service desk."
                )
        else:
            try:
                answer = self.client.complete(
                    "Answer only from the supplied policy context. Say when the context is insufficient. "
                    "Do not make approval decisions. Keep the answer under 140 words.",
                    f"Policy context:\n{context}\n\nRequest context:\n{request_context}\n\nQuestion: {question}",
                )
            except httpx.HTTPError:
                provider = f"{provider}:fallback"
                model = "grounded-template-v1"
                if citations:
                    answer = (
                        "The AI provider is unavailable. Relevant policy: "
                        f"{citations[0].article.content[:430]}"
                    )
                else:
                    answer = (
                        "The AI provider is unavailable and no supporting policy content was found. "
                        "Please contact the service desk."
                    )

        latency_ms = int((perf_counter() - start) * 1000)
        db.add(
            AutomationRun(
                workflow_name="policy_assistant",
                status="success",
                duration_ms=latency_ms,
                provider=provider,
            )
        )
        return AssistantResult(answer, citations, provider, model, latency_ms)


ai_service = AIService()
