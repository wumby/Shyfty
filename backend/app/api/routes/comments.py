from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentRead
from app.services.comment_service import create_comment, delete_comment, list_comments

router = APIRouter()


@router.get("/signals/{signal_id}/comments", response_model=list[CommentRead])
def get_comments(
    signal_id: int,
    db: Session = Depends(get_db),
) -> list[CommentRead]:
    return list_comments(db, signal_id=signal_id)


@router.post("/signals/{signal_id}/comments", response_model=CommentRead, status_code=201)
def post_comment(
    signal_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommentRead:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        return create_comment(db, signal_id=signal_id, user_id=current_user.id, body=payload.body)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/comments/{comment_id}", status_code=204)
def remove_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        delete_comment(db, comment_id=comment_id, user_id=current_user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
