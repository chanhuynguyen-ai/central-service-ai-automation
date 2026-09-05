import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import AuthSession, User
from app.services.audit import record_audit


class RefreshSessionError(RuntimeError):
    pass


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_refresh_session(db: Session, user: User) -> tuple[AuthSession, str]:
    raw_token = _new_refresh_token()
    now = datetime.now(UTC)
    session = AuthSession(
        user_id=user.id,
        refresh_token_hash=hash_refresh_token(raw_token),
        expires_at=now + timedelta(days=settings.refresh_token_expire_days),
    )
    db.add(session)
    return session, raw_token


def rotate_refresh_session(db: Session, refresh_token: str) -> tuple[User, str]:
    now = datetime.now(UTC)
    token_hash = hash_refresh_token(refresh_token)

    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > now,
        )
        .with_for_update()
        .first()
    )
    if session is None:
        raise RefreshSessionError("Invalid or expired refresh token")

    user = (
        db.query(User)
        .filter(
            User.id == session.user_id,
            User.is_active.is_(True),
        )
        .first()
    )
    if user is None:
        raise RefreshSessionError("Refresh session is no longer active")

    replacement, raw_token = create_refresh_session(db, user)
    db.flush()

    session.revoked_at = now
    session.replaced_by_session_id = replacement.id

    return user, raw_token


def revoke_refresh_session(db: Session, refresh_token: str) -> bool:
    token_hash = hash_refresh_token(refresh_token)
    session = (
        db.query(AuthSession)
        .filter(
            AuthSession.refresh_token_hash == token_hash,
            AuthSession.revoked_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if session is None:
        return False

    session.revoked_at = datetime.now(UTC)
    record_audit(db, "auth_logout", actor_id=session.user_id, resource_type="user", resource_id=session.user_id)
    return True
