from collections import defaultdict, deque
from threading import Lock
import time
from typing import Deque, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db, get_session_token
from app.core.config import settings
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
_attempts_lock = Lock()
_auth_attempts: dict[str, Deque[float]] = defaultdict(deque)


def _user_read(user: User) -> UserRead:
    return UserRead(id=user.id, email=user.email, created_at=user.created_at)


def _rate_limit_key(request: Request, email: str) -> str:
    client = request.client.host if request.client else "unknown"
    return f"{client}:{email.strip().lower()}"


def _record_and_check_attempt(key: str) -> bool:
    now = time.monotonic()
    window_seconds = max(1, settings.auth_rate_limit_window_seconds)
    max_attempts = max(1, settings.auth_rate_limit_max_attempts)
    cutoff = now - window_seconds
    with _attempts_lock:
        attempts = _auth_attempts[key]
        while attempts and attempts[0] < cutoff:
            attempts.popleft()
        if len(attempts) >= max_attempts:
            return False
        attempts.append(now)
    return True


def _cookie_options() -> dict:
    return {
        "httponly": True,
        "secure": settings.auth_cookie_secure_effective,
        "samesite": settings.auth_cookie_samesite,
        "max_age": settings.auth_cookie_max_age_seconds,
        "path": "/",
    }


@router.post("/signup", response_model=AuthSessionRead, status_code=status.HTTP_201_CREATED)
def sign_up(payload: UserCreate, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthSessionRead:
    if not _record_and_check_attempt(_rate_limit_key(request, payload.email)):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    try:
        user = create_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_token = create_user_session(db, user_id=user.id)
    response.set_cookie(SESSION_COOKIE_NAME, session_token, **_cookie_options())
    return AuthSessionRead(user=_user_read(user))


@router.post("/signin", response_model=AuthSessionRead)
def sign_in(payload: UserSignIn, request: Request, response: Response, db: Session = Depends(get_db)) -> AuthSessionRead:
    if not _record_and_check_attempt(_rate_limit_key(request, payload.email)):
        raise HTTPException(status_code=429, detail="Too many auth attempts. Try again later.")
    try:
        user = authenticate_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    session_token = create_user_session(db, user_id=user.id)
    response.set_cookie(SESSION_COOKIE_NAME, session_token, **_cookie_options())
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
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=AuthSessionRead)
def get_session(current_user: Optional[User] = Depends(get_current_user)) -> AuthSessionRead:
    return AuthSessionRead(user=_user_read(current_user) if current_user is not None else None)
