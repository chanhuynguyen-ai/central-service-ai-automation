from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, get_current_user, verify_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import (
    LoginInput,
    LogoutInput,
    RefreshTokenInput,
    TokenOut,
    UserOut,
)
from app.services.audit import record_audit
from app.services.auth_sessions import (
    RefreshSessionError,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)
from app.services.permissions import user_role_codes

router = APIRouter()


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        department=user.department,
        role=user.role,
        roles=sorted(user_role_codes(user)),
    )


def _token_response(user: User, refresh_token: str) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.email),
        refresh_token=refresh_token,
        user=_user_out(user),
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        record_audit(db, "auth_login_failed", resource_type="auth")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    _, refresh_token = create_refresh_session(db, user)
    record_audit(db, "auth_login", actor_id=user.id, resource_type="user", resource_id=user.id)
    db.commit()
    return _token_response(user, refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshTokenInput, db: Session = Depends(get_db)) -> TokenOut:
    try:
        user, refresh_token = rotate_refresh_session(db, payload.refresh_token)
    except RefreshSessionError as exc:
        db.rollback()
        record_audit(db, "auth_refresh_failed", resource_type="auth")
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    record_audit(db, "auth_refresh", actor_id=user.id, resource_type="user", resource_id=user.id)
    db.commit()
    return _token_response(user, refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutInput, db: Session = Depends(get_db)) -> Response:
    if not revoke_refresh_session(db, payload.refresh_token):
        record_audit(db, "auth_logout_noop", resource_type="auth")
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
