from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.models import User
from app.schemas.ai_intake import (
    IntakeClassification,
    IntakeDraftRequest,
    IntakeDraftSuggestion,
    IntakeText,
)
from app.services.ai_intake import ai_intake_service

router = APIRouter()


@router.post("/classify", response_model=IntakeClassification)
def classify_intake(
    payload: IntakeText,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IntakeClassification:
    try:
        result = ai_intake_service.classify(db, payload.text)
        db.commit()
        return result
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/draft", response_model=IntakeDraftSuggestion)
def draft_intake(
    payload: IntakeDraftRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> IntakeDraftSuggestion:
    try:
        result = ai_intake_service.draft(db, payload.text, payload.request_type_code)
        db.commit()
        return result
    except LookupError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
