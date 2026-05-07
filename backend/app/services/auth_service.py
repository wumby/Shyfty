from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.models.user_session import UserSession

PASSWORD_RESET_TOKEN_TTL_HOURS = 1

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
    return hmac.new(
        settings.session_secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _is_strong_password(password: str) -> bool:
    if len(password) < 8:
        return False
    has_letter = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_letter and has_digit


def create_user(db: Session, *, email: str, password: str, display_name: Optional[str] = None) -> User:
    normalized_email = _normalize_email(email)
    normalized_display_name = (display_name or "").strip() or normalized_email.split("@", 1)[0]
    user = User(
        email=normalized_email,
        display_name=normalized_display_name[:80],
        password_hash=_hash_password(password),
    )
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


def change_password(
    db: Session,
    *,
    user_id: int,
    current_password: str,
    new_password: str,
    confirm_new_password: str,
) -> None:
    user = db.get(User, user_id)
    if user is None:
        raise AuthError("Authentication required.")
    if not _verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect.")
    if new_password != confirm_new_password:
        raise AuthError("New password and confirm password do not match.")
    if not _is_strong_password(new_password):
        raise AuthError("New password is too weak. Use at least 8 characters with letters and numbers.")
    if _verify_password(new_password, user.password_hash):
        raise AuthError("New password must be different from your current password.")

    user.password_hash = _hash_password(new_password)
    db.add(user)
    db.commit()


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


def _hash_reset_token(token: str) -> str:
    return hmac.new(
        settings.session_secret.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def create_password_reset_token(db: Session, *, email: str) -> Optional[str]:
    """Create a reset token for the given email. Returns the raw token, or None if email not found."""
    user = db.execute(select(User).where(User.email == _normalize_email(email))).scalar_one_or_none()
    if user is None:
        return None

    raw_token = secrets.token_urlsafe(32)
    record = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_reset_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(hours=PASSWORD_RESET_TOKEN_TTL_HOURS),
    )
    db.add(record)
    db.commit()
    return raw_token


def consume_password_reset_token(db: Session, *, token: str, new_password: str) -> None:
    """Validate token, update password, revoke all sessions. Raises AuthError on failure."""
    record = db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash_reset_token(token))
    ).scalar_one_or_none()

    if record is None or record.used_at is not None:
        raise AuthError("This reset link is invalid or has already been used.")
    if datetime.utcnow() > record.expires_at:
        raise AuthError("This reset link has expired. Please request a new one.")
    if not _is_strong_password(new_password):
        raise AuthError("Password must be at least 8 characters with letters and numbers.")

    user = db.get(User, record.user_id)
    if user is None:
        raise AuthError("Account not found.")

    user.password_hash = _hash_password(new_password)
    record.used_at = datetime.utcnow()
    db.execute(delete(UserSession).where(UserSession.user_id == user.id))
    db.commit()
