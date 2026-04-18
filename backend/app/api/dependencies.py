from collections.abc import Generator
from typing import Optional

from fastapi import Cookie, Depends

from app.db.session import SessionLocal
from app.models.user import User
from app.services.auth_service import SESSION_COOKIE_NAME, get_user_by_session_token


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db=Depends(get_db),
) -> Optional[User]:
    return get_user_by_session_token(db, session_token)


def get_session_token(
    session_token: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> Optional[str]:
    return session_token
