import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.models import KnowledgeArticle


@dataclass
class RetrievedArticle:
    article: KnowledgeArticle
    score: float


def tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def retrieve_articles(db: Session, question: str, limit: int = 3) -> list[RetrievedArticle]:
    query_tokens = tokenize(question)
    articles = db.query(KnowledgeArticle).filter(KnowledgeArticle.is_active.is_(True)).all()
    scored: list[RetrievedArticle] = []

    for article in articles:
        title_tokens = tokenize(article.title)
        content_tokens = tokenize(article.content)
        title_overlap = len(query_tokens & title_tokens)
        content_overlap = len(query_tokens & content_tokens)
        score = title_overlap * 2.0 + content_overlap * 0.5
        if score > 0:
            normalized = min(1.0, score / max(3.0, len(query_tokens)))
            scored.append(RetrievedArticle(article=article, score=round(normalized, 3)))

    scored.sort(key=lambda item: item.score, reverse=True)
    if scored:
        return scored[:limit]

    return [RetrievedArticle(article=article, score=0.1) for article in articles[:1]]
