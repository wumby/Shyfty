from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import secrets
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.user_session import UserSession

SESSION_COOKIE_NAME = "shyfty_session"


class AuthError(ValueError):
    pass


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _hash_password(password: str, *, salt: Optional[str] = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(password_salt), 120000)
    return f"{password_salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    salt, _ = password_hash.split("$", 1)
    return hmac.compare_digest(_hash_password(password, salt=salt), password_hash)


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_user(db: Session, *, email: str, password: str) -> User:
    normalized_email = _normalize_email(email)
    user = User(email=normalized_email, password_hash=_hash_password(password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AuthError("An account with that email already exists.") from exc
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User:
    user = db.execute(select(User).where(User.email == _normalize_email(email))).scalar_one_or_none()
    if user is None or not _verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.")
    return user


def create_user_session(db: Session, *, user_id: int) -> str:
    raw_token = secrets.token_urlsafe(32)
    session = UserSession(user_id=user_id, token_hash=_hash_session_token(raw_token))
    db.add(session)
    db.commit()
    return raw_token


def get_user_by_session_token(db: Session, token: Optional[str]) -> Optional[User]:
    if not token:
        return None

    session = db.execute(
        select(UserSession).where(UserSession.token_hash == _hash_session_token(token))
    ).scalar_one_or_none()
    if session is None:
        return None

    session.updated_at = datetime.utcnow()
    db.commit()
    return db.execute(select(User).where(User.id == session.user_id)).scalar_one_or_none()


def revoke_session(db: Session, token: Optional[str]) -> None:
    if not token:
        return
    db.execute(delete(UserSession).where(UserSession.token_hash == _hash_session_token(token)))
    db.commit()
