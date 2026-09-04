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
from app.services.auth_sessions import (
    RefreshSessionError,
    create_refresh_session,
    revoke_refresh_session,
    rotate_refresh_session,
)

router = APIRouter()


def _token_response(user: User, refresh_token: str) -> TokenOut:
    return TokenOut(
        access_token=create_access_token(user.email),
        refresh_token=refresh_token,
        user=UserOut.model_validate(user),
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginInput, db: Session = Depends(get_db)) -> TokenOut:
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    _, refresh_token = create_refresh_session(db, user)
    db.commit()
    return _token_response(user, refresh_token)


@router.post("/refresh", response_model=TokenOut)
def refresh(payload: RefreshTokenInput, db: Session = Depends(get_db)) -> TokenOut:
    try:
        user, refresh_token = rotate_refresh_session(db, payload.refresh_token)
    except RefreshSessionError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    db.commit()
    return _token_response(user, refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutInput, db: Session = Depends(get_db)) -> Response:
    revoke_refresh_session(db, payload.refresh_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
