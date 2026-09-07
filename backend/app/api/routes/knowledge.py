from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.knowledge import PolicyDocument
from app.models.models import User
from app.schemas.knowledge import (
    PolicyAnswer,
    PolicyDocumentCreate,
    PolicyDocumentOut,
    PolicyQuestion,
)
from app.services.audit import record_audit
from app.services.knowledge import (
    PolicyConflictError,
    PolicyValidationError,
    answer_policy_question,
    create_policy_document,
    serialize_policy_document,
)

router = APIRouter()


@router.post("/documents", response_model=PolicyDocumentOut, status_code=status.HTTP_201_CREATED)
def create_document(
    payload: PolicyDocumentCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_roles("ADMIN")),
) -> PolicyDocumentOut:
    try:
        document = create_policy_document(db, payload, actor)
        record_audit(
            db,
            "policy_document_indexed",
            actor_id=actor.id,
            resource_type="policy_document",
            resource_id=document.id,
            details={
                "document_id": document.id,
                "version": document.version,
                "access_scope": document.access_scope,
                "status": document.status,
            },
        )
        db.commit()
        db.refresh(document)
        return serialize_policy_document(document)
    except PolicyConflictError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except PolicyValidationError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/documents", response_model=list[PolicyDocumentOut])
def list_documents(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("ADMIN", "AUDITOR")),
) -> list[PolicyDocumentOut]:
    documents = db.query(PolicyDocument).order_by(PolicyDocument.id.desc()).all()
    return [serialize_policy_document(document) for document in documents]


@router.post("/ask", response_model=PolicyAnswer)
def ask_policy(
    payload: PolicyQuestion,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_user),
) -> PolicyAnswer:
    result = answer_policy_question(db, actor, payload.question, payload.top_k)
    db.commit()
    return result
