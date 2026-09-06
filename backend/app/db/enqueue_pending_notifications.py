from app.db.session import SessionLocal
from app.notification_tasks import deliver_notification
from app.services.notifications import email_candidates


def main() -> None:
    db = SessionLocal()
    try:
        ids = email_candidates(db, limit=200)
    finally:
        db.close()
    for notification_id in ids:
        deliver_notification.send(notification_id)


if __name__ == "__main__":
    main()
