import smtplib
from email.message import EmailMessage

import dramatiq
from dramatiq.brokers.redis import RedisBroker

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.models import User
from app.models.notifications import Notification
from app.services.notifications import mark_email_failed, mark_email_sent

broker = RedisBroker(url=settings.redis_url)
dramatiq.set_broker(broker)


def _send_email(row: Notification, recipient: User) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = recipient.email
    message["Subject"] = row.subject
    message.set_content(row.body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(message)


@dramatiq.actor(max_retries=0)
def deliver_notification(notification_id: int) -> None:
    db = SessionLocal()
    try:
        row = (
            db.query(Notification)
            .filter_by(id=notification_id, channel="EMAIL")
            .populate_existing()
            .with_for_update()
            .first()
        )
        if row is None or row.status in {"SENT", "DEAD"}:
            return
        recipient = db.get(User, row.recipient_user_id)
        if recipient is None or not recipient.is_active:
            mark_email_failed(
                db,
                row,
                error="Recipient is unavailable or inactive",
                retry_seconds=settings.notification_retry_seconds,
                max_attempts=1,
            )
            db.commit()
            return
        try:
            _send_email(row, recipient)
        except Exception as exc:
            mark_email_failed(
                db,
                row,
                error=f"{type(exc).__name__}: {exc}",
                retry_seconds=settings.notification_retry_seconds,
                max_attempts=settings.notification_max_attempts,
            )
        else:
            mark_email_sent(db, row)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
