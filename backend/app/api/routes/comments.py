from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead, CommentReportCreate, CommentUpdate
from app.services.abuse_service import enforce_rate_limit
from app.services.comment_service import (
    create_comment,
    delete_comment,
    list_comments,
    report_comment,
    update_comment,
)

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.get("/signals/{signal_id}/comments", response_model=list[CommentRead])
def get_comments(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[CommentRead]:
    return list_comments(db, signal_id=signal_id, current_user_id=current_user.id if current_user else None)


@router.post("/signals/{signal_id}/comments", response_model=CommentRead, status_code=201)
def post_comment(
    signal_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> CommentRead:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "comment_post", limit=8, per_seconds=300)
    try:
        return create_comment(db, signal_id=signal_id, user_id=user.id, body=payload.body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put("/comments/{comment_id}", response_model=CommentRead)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> CommentRead:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "comment_edit", limit=20, per_seconds=600)
    try:
        return update_comment(db, comment_id=comment_id, user_id=user.id, body=payload.body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/comments/{comment_id}/report", status_code=202)
def report_comment_route(
    comment_id: int,
    payload: CommentReportCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "comment_report", limit=15, per_seconds=3600)
    try:
        return report_comment(
            db,
            comment_id=comment_id,
            reporter_user_id=user.id,
            reason=payload.reason,
            notes=payload.notes,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/comments/{comment_id}", status_code=204)
def remove_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    try:
        delete_comment(db, comment_id=comment_id, user_id=user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
