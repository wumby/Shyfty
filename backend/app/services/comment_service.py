from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_comment import SignalComment
from app.models.user import User
from app.schemas.comment import CommentRead


def list_comments(db: Session, signal_id: int) -> list[CommentRead]:
    rows = db.execute(
        select(SignalComment, User.email)
        .join(User, SignalComment.user_id == User.id)
        .where(SignalComment.signal_id == signal_id)
        .order_by(SignalComment.created_at.asc())
    ).all()
    return [
        CommentRead(
            id=comment.id,
            signal_id=comment.signal_id,
            user_id=comment.user_id,
            user_email=email,
            body=comment.body,
            created_at=comment.created_at,
        )
        for comment, email in rows
    ]


def create_comment(db: Session, *, signal_id: int, user_id: int, body: str) -> CommentRead:
    signal_exists = db.execute(select(Signal.id).where(Signal.id == signal_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Signal not found.")

    comment = SignalComment(signal_id=signal_id, user_id=user_id, body=body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)

    user = db.get(User, user_id)
    return CommentRead(
        id=comment.id,
        signal_id=comment.signal_id,
        user_id=comment.user_id,
        user_email=user.email if user else "",
        body=comment.body,
        created_at=comment.created_at,
    )


def delete_comment(db: Session, *, comment_id: int, user_id: int) -> None:
    comment = db.execute(
        select(SignalComment).where(SignalComment.id == comment_id)
    ).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    if comment.user_id != user_id:
        raise PermissionError("Not your comment.")
    db.delete(comment)
    db.commit()
