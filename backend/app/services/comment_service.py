from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comment_report import CommentReport
from app.models.signal import Signal
from app.models.signal_comment import SignalComment
from app.models.user import User
from app.schemas.comment import CommentRead


def _comment_read(comment: SignalComment, email: str, current_user_id: Optional[int]) -> CommentRead:
    return CommentRead(
        id=comment.id,
        signal_id=comment.signal_id,
        user_id=comment.user_id,
        user_email=email,
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        is_edited=comment.updated_at > comment.created_at,
        can_edit=current_user_id == comment.user_id,
        can_delete=current_user_id == comment.user_id,
        can_report=current_user_id is not None and current_user_id != comment.user_id,
    )


def list_comments(db: Session, signal_id: int, current_user_id: Optional[int] = None) -> list[CommentRead]:
    rows = db.execute(
        select(SignalComment, User.email)
        .join(User, SignalComment.user_id == User.id)
        .where(SignalComment.signal_id == signal_id)
        .order_by(SignalComment.created_at.asc())
    ).all()
    return [_comment_read(comment, email, current_user_id) for comment, email in rows]


def list_discussion_preview(
    db: Session,
    signal_id: int,
    current_user_id: Optional[int] = None,
    limit: int = 3,
) -> list[CommentRead]:
    rows = db.execute(
        select(SignalComment, User.email)
        .join(User, SignalComment.user_id == User.id)
        .where(SignalComment.signal_id == signal_id)
        .order_by(SignalComment.created_at.desc())
        .limit(limit)
    ).all()
    return [_comment_read(comment, email, current_user_id) for comment, email in rows]


def create_comment(db: Session, *, signal_id: int, user_id: int, body: str) -> CommentRead:
    signal_exists = db.execute(select(Signal.id).where(Signal.id == signal_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Signal not found.")

    comment = SignalComment(signal_id=signal_id, user_id=user_id, body=body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)

    user = db.get(User, user_id)
    return _comment_read(comment, user.email if user else "", user_id)


def update_comment(db: Session, *, comment_id: int, user_id: int, body: str) -> CommentRead:
    comment = db.execute(select(SignalComment).where(SignalComment.id == comment_id)).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    if comment.user_id != user_id:
        raise PermissionError("Not your comment.")
    comment.body = body.strip()
    db.add(comment)
    db.commit()
    db.refresh(comment)
    user = db.get(User, user_id)
    return _comment_read(comment, user.email if user else "", user_id)


def delete_comment(db: Session, *, comment_id: int, user_id: int) -> None:
    comment = db.execute(select(SignalComment).where(SignalComment.id == comment_id)).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    if comment.user_id != user_id:
        raise PermissionError("Not your comment.")
    db.delete(comment)
    db.commit()


def report_comment(db: Session, *, comment_id: int, reporter_user_id: int, reason: str, notes: Optional[str]) -> dict:
    comment = db.execute(select(SignalComment).where(SignalComment.id == comment_id)).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    existing = db.execute(
        select(CommentReport).where(
            CommentReport.comment_id == comment_id,
            CommentReport.reporter_user_id == reporter_user_id,
        )
    ).scalar_one_or_none()
    if existing is None:
        db.add(
            CommentReport(
                comment_id=comment_id,
                reporter_user_id=reporter_user_id,
                reason=reason.strip().lower().replace(" ", "_"),
                notes=notes.strip() if notes else None,
            )
        )
        db.commit()
    open_count = db.execute(
        select(func.count(CommentReport.id)).where(
            CommentReport.comment_id == comment_id,
            CommentReport.status == "open",
        )
    ).scalar_one()
    return {"comment_id": comment_id, "status": "reported", "open_report_count": open_count}
