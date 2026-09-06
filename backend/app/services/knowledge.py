import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter

import httpx
from sqlalchemy import bindparam, or_, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import PolicyChunk, PolicyDocument
from app.models.models import AutomationRun, Department, User
from app.schemas.knowledge import (
    PolicyAnswer,
    PolicyCitation,
    PolicyDocumentCreate,
    PolicyDocumentOut,
)
from app.services.llm import LLMClient
from app.services.permissions import normalize_role_code, user_role_codes

EMBEDDING_DIMENSIONS = 64
TOKEN = re.compile(r"[a-z0-9]+")
HEADING = re.compile(r"^#{1,6}\s+(.+)$")
MIN_GROUNDED_SCORE = 0.16


class PolicyConflictError(Exception):
    pass


class PolicyValidationError(Exception):
    pass


@dataclass
class RetrievedPolicyChunk:
    chunk: PolicyChunk
    document: PolicyDocument
    score: float


def _normalize(vector: list[float]) -> list[float]:
    magnitude = math.sqrt(sum(value * value for value in vector))
    if magnitude == 0:
        return [0.0] * len(vector)
    return [value / magnitude for value in vector]


def _project_vector(values: list[float]) -> list[float]:
    if not values:
        raise ValueError("Embedding provider returned an empty vector")
    projected = [0.0] * EMBEDDING_DIMENSIONS
    for index, value in enumerate(values):
        projected[index % EMBEDDING_DIMENSIONS] += float(value)
    return _normalize(projected)


def deterministic_embedding(value: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    tokens = TOKEN.findall(value.lower())
    features = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign
    return _normalize(vector)


def embed_text(value: str) -> tuple[list[float], str]:
    provider = settings.llm_provider
    if provider == "mock":
        return deterministic_embedding(value), "mock:hash-embedding-v1"
    try:
        if provider == "ollama":
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/api/embed",
                json={"model": settings.embedding_model, "input": value},
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            raw = response.json()["embeddings"][0]
        elif provider == "openai_compatible":
            response = httpx.post(
                f"{settings.llm_base_url.rstrip('/')}/v1/embeddings",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={"model": settings.embedding_model, "input": value},
                timeout=settings.llm_timeout_seconds,
            )
            response.raise_for_status()
            raw = response.json()["data"][0]["embedding"]
        else:
            raise ValueError("Unsupported embedding provider")
        return _project_vector([float(item) for item in raw]), provider
    except (httpx.HTTPError, KeyError, TypeError, ValueError, IndexError):
        return deterministic_embedding(value), f"{provider}:embedding-fallback"


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def chunk_policy_text(content: str, max_chars: int = 900) -> list[tuple[str, str | None]]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
    chunks: list[tuple[str, str | None]] = []
    current = ""
    section: str | None = None
    current_section: str | None = None
    for paragraph in paragraphs:
        heading = HEADING.match(paragraph.splitlines()[0])
        if heading:
            section = heading.group(1).strip()[:220]
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append((current, current_section))
            current = ""
        if not current:
            current_section = section
        if len(paragraph) <= max_chars:
            current = f"{current}\n\n{paragraph}".strip()
            continue
        if current:
            chunks.append((current, current_section))
            current = ""
        for start in range(0, len(paragraph), max_chars):
            chunks.append((paragraph[start : start + max_chars], section))
    if current:
        chunks.append((current, current_section))
    return chunks


def _insert_chunk(
    db: Session,
    document_id: int,
    chunk_index: int,
    content: str,
    section: str | None,
    embedding: list[float],
) -> None:
    literal = vector_literal(embedding)
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text(
                """
                INSERT INTO policy_chunks
                    (document_id, chunk_index, content, page, section, embedding, created_at)
                VALUES
                    (:document_id, :chunk_index, :content, NULL, :section,
                     CAST(:embedding AS vector), :created_at)
                """
            ),
            {
                "document_id": document_id,
                "chunk_index": chunk_index,
                "content": content,
                "section": section,
                "embedding": literal,
                "created_at": datetime.now(UTC),
            },
        )
    else:
        db.add(
            PolicyChunk(
                document_id=document_id,
                chunk_index=chunk_index,
                content=content,
                section=section,
                embedding=json.dumps(embedding),
            )
        )


def create_policy_document(
    db: Session,
    payload: PolicyDocumentCreate,
    actor: User,
) -> PolicyDocument:
    existing = (
        db.query(PolicyDocument)
        .filter(PolicyDocument.slug == payload.slug, PolicyDocument.version == payload.version)
        .first()
    )
    if existing:
        raise PolicyConflictError("This policy slug/version already exists")
    if payload.department_id is not None:
        department = db.get(Department, payload.department_id)
        if department is None or not department.is_active:
            raise PolicyValidationError("Department scope must reference an active department")

    role_code = normalize_role_code(payload.role_code) if payload.role_code else None
    checksum = hashlib.sha256(payload.content.encode("utf-8")).hexdigest()
    document = PolicyDocument(
        slug=payload.slug,
        title=payload.title,
        version=payload.version,
        source_name=payload.source_name,
        status=payload.status,
        access_scope=payload.access_scope,
        department_id=payload.department_id,
        role_code=role_code,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        checksum_sha256=checksum,
        created_by=actor.id,
    )
    db.add(document)
    db.flush()

    chunks = chunk_policy_text(payload.content)
    if not chunks:
        raise PolicyValidationError("Policy content did not produce any indexable chunks")
    for index, (chunk, section) in enumerate(chunks):
        embedding, _ = embed_text(chunk)
        _insert_chunk(db, document.id, index, chunk, section, embedding)
    db.flush()
    return document


def serialize_policy_document(document: PolicyDocument) -> PolicyDocumentOut:
    return PolicyDocumentOut(
        id=document.id,
        slug=document.slug,
        title=document.title,
        version=document.version,
        source_name=document.source_name,
        status=document.status,
        is_active=document.is_active,
        access_scope=document.access_scope,
        department_id=document.department_id,
        role_code=document.role_code,
        effective_from=document.effective_from,
        effective_to=document.effective_to,
        checksum_sha256=document.checksum_sha256,
        created_by=document.created_by,
        created_at=document.created_at,
        chunk_count=len(document.chunks),
    )


def accessible_policy_documents(db: Session, actor: User) -> list[PolicyDocument]:
    now = datetime.now(UTC)
    documents = (
        db.query(PolicyDocument)
        .filter(
            PolicyDocument.is_active.is_(True),
            PolicyDocument.status == "PUBLISHED",
            or_(PolicyDocument.effective_from.is_(None), PolicyDocument.effective_from <= now),
            or_(PolicyDocument.effective_to.is_(None), PolicyDocument.effective_to >= now),
        )
        .order_by(PolicyDocument.id.asc())
        .all()
    )
    roles = user_role_codes(actor)
    allowed: list[PolicyDocument] = []
    for document in documents:
        if document.access_scope == "ALL":
            allowed.append(document)
        elif document.access_scope == "DEPARTMENT" and document.department_id == actor.department_id:
            allowed.append(document)
        elif document.access_scope == "ROLE" and document.role_code in roles:
            allowed.append(document)
    return allowed


def retrieve_policy_chunks(
    db: Session,
    actor: User,
    question: str,
    limit: int = 4,
) -> list[RetrievedPolicyChunk]:
    documents = accessible_policy_documents(db, actor)
    if not documents:
        return []
    document_by_id = {document.id: document for document in documents}
    query_vector, _ = embed_text(question)
    ids = list(document_by_id)

    scored: list[tuple[int, float]] = []
    if db.get_bind().dialect.name == "postgresql":
        statement = text(
            """
            SELECT id,
                   1 - (embedding <=> CAST(:query_embedding AS vector)) AS score
            FROM policy_chunks
            WHERE document_id IN :document_ids
            ORDER BY embedding <=> CAST(:query_embedding AS vector), id
            LIMIT :limit
            """
        ).bindparams(bindparam("document_ids", expanding=True))
        rows = db.execute(
            statement,
            {
                "query_embedding": vector_literal(query_vector),
                "document_ids": ids,
                "limit": limit,
            },
        ).all()
        scored = [(int(row.id), float(row.score)) for row in rows]
    else:
        chunks = db.query(PolicyChunk).filter(PolicyChunk.document_id.in_(ids)).all()
        for chunk in chunks:
            stored = [float(item) for item in json.loads(chunk.embedding)]
            scored.append((chunk.id, _cosine(query_vector, stored)))
        scored.sort(key=lambda item: (-item[1], item[0]))
        scored = scored[:limit]

    result: list[RetrievedPolicyChunk] = []
    for chunk_id, score in scored:
        chunk = db.get(PolicyChunk, chunk_id)
        if chunk is None or chunk.document_id not in document_by_id:
            continue
        result.append(
            RetrievedPolicyChunk(
                chunk=chunk,
                document=document_by_id[chunk.document_id],
                score=max(-1.0, min(1.0, round(score, 4))),
            )
        )
    return result


def answer_policy_question(
    db: Session,
    actor: User,
    question: str,
    top_k: int = 4,
) -> PolicyAnswer:
    started = perf_counter()
    retrieved = retrieve_policy_chunks(db, actor, question, top_k)
    grounded = [item for item in retrieved if item.score >= settings.rag_min_score]
    provider = settings.llm_provider
    model = settings.llm_model if provider != "mock" else "grounded-policy-template-v2"

    if not grounded:
        answer = (
            "I could not find enough accessible, currently effective policy evidence to answer that "
            "question. Please contact the relevant service owner or administrator."
        )
        insufficient = True
    else:
        insufficient = False
        if provider == "mock":
            source = grounded[0]
            answer = (
                f"According to {source.document.title} v{source.document.version}: "
                f"{source.chunk.content[:650].strip()}"
            )
        else:
            context = "\n\n".join(
                f"[Source {index}: {item.document.title} v{item.document.version}; "
                f"section={item.chunk.section or 'n/a'}]\n{item.chunk.content}"
                for index, item in enumerate(grounded, start=1)
            )
            try:
                answer = LLMClient().complete(
                    "Answer only from the supplied accessible policy chunks. Do not make approval "
                    "decisions or invent policy. If the evidence is insufficient, say so clearly.",
                    f"Accessible policy evidence:\n{context}\n\nQuestion: {question}",
                )
            except httpx.HTTPError:
                provider = f"{provider}:fallback"
                model = "grounded-policy-template-v2"
                source = grounded[0]
                answer = (
                    f"The model provider is unavailable. Relevant accessible policy evidence from "
                    f"{source.document.title} v{source.document.version}: "
                    f"{source.chunk.content[:650].strip()}"
                )

    citations = [
        PolicyCitation(
            document_id=item.document.id,
            chunk_id=item.chunk.id,
            title=item.document.title,
            version=item.document.version,
            source_name=item.document.source_name,
            page=item.chunk.page,
            section=item.chunk.section,
            score=item.score,
        )
        for item in grounded
    ]
    latency_ms = int((perf_counter() - started) * 1000)
    db.add(
        AutomationRun(
            workflow_name="policy_rag",
            status="insufficient_evidence" if insufficient else "success",
            duration_ms=latency_ms,
            provider=provider,
        )
    )
    return PolicyAnswer(
        answer=answer,
        grounded=bool(citations),
        insufficient_evidence=insufficient,
        citations=citations,
        provider=provider,
        model=model,
        latency_ms=latency_ms,
    )
