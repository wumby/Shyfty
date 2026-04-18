from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_session_token
from app.models.user import User
from app.schemas.auth import AuthSessionRead, UserCreate, UserRead, UserSignIn
from app.services.auth_service import (
    AuthError,
    SESSION_COOKIE_NAME,
    authenticate_user,
    create_user,
    create_user_session,
    revoke_session,
)

router = APIRouter(prefix="/auth")


def _user_read(user: User) -> UserRead:
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)


@router.post("/signup", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def sign_up(payload: UserCreate, response: Response, db: Session = Depends(get_db)) -> AuthSessionRead:
    try:
        user = create_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_token = create_user_session(db, user_id=user.id)
    response.set_cookie(SESSION_COOKIE_NAME, session_token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return AuthSessionRead(user=_user_read(user))


@router.post("/signin", response_model=AuthSessionRead)
def sign_in(payload: UserSignIn, response: Response, db: Session = Depends(get_db)) -> AuthSessionRead:
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_token = create_user_session(db, user_id=user.id)
    response.set_cookie(SESSION_COOKIE_NAME, session_token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 30)
    return AuthSessionRead(user=_user_read(user))


@router.post("/signout", status_code=status.HTTP_204_NO_CONTENT)
def sign_out(
    response: Response,
    current_user: Optional[User] = Depends(get_current_user),
    session_token: Optional[str] = Depends(get_session_token),
    db: Session = Depends(get_db),
) -> Response:
    del current_user
    revoke_session(db, session_token)
    response.delete_cookie(SESSION_COOKIE_NAME)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthSessionRead)
def get_session(current_user: Optional[User] = Depends(get_current_user)) -> AuthSessionRead:
    return AuthSessionRead(user=_user_read(current_user) if current_user is not None else None)
