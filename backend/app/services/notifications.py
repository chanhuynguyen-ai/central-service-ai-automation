from datetime import UTC, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import User
from app.models.notifications import Notification


class NotificationError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _now() -> datetime:
    return datetime.now(UTC)


def enqueue_pair(
    db: Session,
    *,
    recipient: User,
    event_key: str,
    kind: str,
    subject: str,
    body: str,
    request_id: int | None = None,
) -> list[Notification]:
    if not recipient.is_active:
        return []
    created: list[Notification] = []
    for channel in ("IN_APP", "EMAIL"):
        existing = db.query(Notification).filter_by(event_key=event_key, channel=channel).first()
        if existing:
            created.append(existing)
            continue
        row = Notification(
            recipient_user_id=recipient.id,
            request_id=request_id,
            event_key=event_key,
            kind=kind,
            channel=channel,
            subject=subject,
            body=body,
            status="PENDING" if channel == "EMAIL" else "SENT",
            sent_at=None if channel == "EMAIL" else _now(),
        )
        db.add(row)
        created.append(row)
    db.flush()
    return created


def list_in_app(
    db: Session,
    actor: User,
    *,
    unread_only: bool,
    limit: int,
    offset: int,
) -> dict:
    query = db.query(Notification).filter(
        Notification.recipient_user_id == actor.id,
        Notification.channel == "IN_APP",
    )
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    total = query.count()
    rows = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    unread = db.query(func.count(Notification.id)).filter(
        Notification.recipient_user_id == actor.id,
        Notification.channel == "IN_APP",
        Notification.read_at.is_(None),
    ).scalar() or 0
    return {"items": rows, "total": total, "unread": unread}


def mark_read(db: Session, actor: User, notification_id: int) -> Notification:
    row = db.query(Notification).filter_by(
        id=notification_id,
        recipient_user_id=actor.id,
        channel="IN_APP",
    ).first()
    if row is None:
        raise NotificationError(404, "Notification not found")
    if row.read_at is None:
        row.read_at = _now()
        row.status = "READ"
        row.updated_at = _now()
        db.flush()
    return row


def mark_all_read(db: Session, actor: User) -> int:
    now = _now()
    rows = db.query(Notification).filter(
        Notification.recipient_user_id == actor.id,
        Notification.channel == "IN_APP",
        Notification.read_at.is_(None),
    ).all()
    for row in rows:
        row.read_at = now
        row.status = "READ"
        row.updated_at = now
    db.flush()
    return len(rows)


def email_candidates(db: Session, *, limit: int = 100) -> list[int]:
    now = _now()
    rows = (
        db.query(Notification.id)
        .filter(
            Notification.channel == "EMAIL",
            Notification.status.in_(["PENDING", "FAILED"]),
            Notification.available_at <= now,
        )
        .order_by(Notification.available_at, Notification.id)
        .limit(limit)
        .all()
    )
    return [row[0] for row in rows]


def mark_email_sent(db: Session, row: Notification) -> None:
    row.status = "SENT"
    row.sent_at = _now()
    row.last_error = None
    row.updated_at = _now()
    db.flush()


def mark_email_failed(
    db: Session,
    row: Notification,
    *,
    error: str,
    retry_seconds: int,
    max_attempts: int,
) -> None:
    row.attempts += 1
    row.last_error = error[:500]
    row.updated_at = _now()
    if row.attempts >= max_attempts:
        row.status = "DEAD"
    else:
        row.status = "FAILED"
        row.available_at = _now() + timedelta(seconds=retry_seconds * max(1, row.attempts))
    db.flush()
