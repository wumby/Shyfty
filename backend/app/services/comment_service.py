from __future__ import annotations

from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.comment_report import CommentReport
from app.models.shyft import Shyft
from app.models.shyft_comment import ShyftComment
from app.models.user import User
from app.schemas.comment import CommentRead


def _display_name(display_name: Optional[str], email: str) -> str:
    clean = (display_name or "").strip()
    if clean:
        return clean
    return email.split("@", 1)[0] if "@" in email else email


def _comment_read(comment: ShyftComment, email: str, display_name: Optional[str], current_user_id: Optional[int]) -> CommentRead:
    return CommentRead(
        id=comment.id,
        shyft_id=comment.shyft_id,
        user_id=comment.user_id,
        user_email=email,
        user_display_name=_display_name(display_name, email),
        body=comment.body,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        is_edited=comment.updated_at > comment.created_at,
        can_edit=current_user_id == comment.user_id,
        can_delete=current_user_id == comment.user_id,
        can_report=current_user_id is not None and current_user_id != comment.user_id,
    )


def _signal_group_ids(db: Session, shyft_id: int) -> list[int]:
    shyft = db.execute(select(Shyft).where(Shyft.id == shyft_id)).scalar_one_or_none()
    if shyft is None:
        return []

    same_group = [
        Shyft.game_id == shyft.game_id,
        Shyft.subject_type == shyft.subject_type,
    ]
    if shyft.player_id is not None:
        same_group.append(Shyft.player_id == shyft.player_id)
    else:
        same_group.extend([Shyft.player_id.is_(None), Shyft.team_id == shyft.team_id])

    return list(
        db.execute(
            select(Shyft.id)
            .where(and_(*same_group))
            .order_by(func.coalesce(Shyft.shyft_score, 0).desc(), Shyft.id.asc())
        ).scalars()
    )


def list_comments(
    db: Session,
    shyft_id: Optional[int] = None,
    current_user_id: Optional[int] = None,
    signal_id: Optional[int] = None,
) -> list[CommentRead]:
    shyft_id = shyft_id if shyft_id is not None else signal_id
    if shyft_id is None:
        return []
    signal_ids = _signal_group_ids(db, shyft_id)
    if not signal_ids:
        return []
    rows = db.execute(
        select(ShyftComment, User.email, User.display_name)
        .join(User, ShyftComment.user_id == User.id)
        .where(ShyftComment.shyft_id.in_(signal_ids))
        .order_by(ShyftComment.created_at.asc())
    ).all()
    return [_comment_read(comment, email, display_name, current_user_id) for comment, email, display_name in rows]


def list_discussion_preview(
    db: Session,
    shyft_id: int,
    current_user_id: Optional[int] = None,
    limit: int = 3,
) -> list[CommentRead]:
    signal_ids = _signal_group_ids(db, shyft_id)
    if not signal_ids:
        return []
    rows = db.execute(
        select(ShyftComment, User.email, User.display_name)
        .join(User, ShyftComment.user_id == User.id)
        .where(ShyftComment.shyft_id.in_(signal_ids))
        .order_by(ShyftComment.created_at.desc())
        .limit(limit)
    ).all()
    return [_comment_read(comment, email, display_name, current_user_id) for comment, email, display_name in rows]


def create_comment(
    db: Session,
    *,
    shyft_id: Optional[int] = None,
    signal_id: Optional[int] = None,
    user_id: int,
    body: str,
) -> CommentRead:
    shyft_id = shyft_id if shyft_id is not None else signal_id
    if shyft_id is None:
        raise LookupError("Shyft not found.")
    signal_ids = _signal_group_ids(db, shyft_id)
    if not signal_ids:
        raise LookupError("Shyft not found.")

    comment = ShyftComment(shyft_id=signal_ids[0], user_id=user_id, body=body.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)

    user = db.get(User, user_id)
    return _comment_read(comment, user.email if user else "", user.display_name if user else None, user_id)


def update_comment(db: Session, *, comment_id: int, user_id: int, body: str) -> CommentRead:
    comment = db.execute(select(ShyftComment).where(ShyftComment.id == comment_id)).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    if comment.user_id != user_id:
        raise PermissionError("Not your comment.")
    comment.body = body.strip()
    db.add(comment)
    db.commit()
    db.refresh(comment)
    user = db.get(User, user_id)
    return _comment_read(comment, user.email if user else "", user.display_name if user else None, user_id)


def delete_comment(db: Session, *, comment_id: int, user_id: int) -> None:
    comment = db.execute(select(ShyftComment).where(ShyftComment.id == comment_id)).scalar_one_or_none()
    if comment is None:
        raise LookupError("Comment not found.")
    if comment.user_id != user_id:
        raise PermissionError("Not your comment.")
    db.delete(comment)
    db.commit()


def report_comment(db: Session, *, comment_id: int, reporter_user_id: int, reason: str, notes: Optional[str]) -> dict:
    comment = db.execute(select(ShyftComment).where(ShyftComment.id == comment_id)).scalar_one_or_none()
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
