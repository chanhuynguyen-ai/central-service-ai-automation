from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import ServiceRequest, User
from app.schemas.schemas import AssistantAnswer, AssistantQuestion, CitationOut
from app.services.llm import ai_service
from app.services.permissions import can_view_request

router = APIRouter()


@router.post("/chat", response_model=AssistantAnswer)
def chat(
    payload: AssistantQuestion,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssistantAnswer:
    request_context = ""
    if payload.request_reference:
        request = (
            db.query(ServiceRequest).filter(ServiceRequest.status != "draft")
            .filter(ServiceRequest.reference == payload.request_reference)
            .first()
        )
        if not request or not can_view_request(user, request):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
        request_context = (
            f"Reference: {request.reference}; category: {request.category}; priority: "
            f"{request.priority}; status: {request.status}; title: {request.title}"
        )

    result = ai_service.answer(db, payload.question, request_context)
    db.commit()
    return AssistantAnswer(
        answer=result.answer,
        citations=[
            CitationOut(
                article_id=item.article.id,
                title=item.article.title,
                version=item.article.version,
                score=item.score,
            )
            for item in result.citations
        ],
        provider=result.provider,
        model=result.model,
        grounded=bool(result.citations),
        latency_ms=result.latency_ms,
    )
