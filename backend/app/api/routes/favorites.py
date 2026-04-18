from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.signal import PaginatedSignals
from app.services.favorite_service import add_favorite, list_favorite_signal_ids, remove_favorite
from app.services.signal_service import list_signals

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.post("/favorites/{signal_id}", status_code=status.HTTP_201_CREATED)
def add_to_favorites(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> dict:
    user = _require_user(current_user)
    add_favorite(db, user_id=user.id, signal_id=signal_id)
    return {"signal_id": signal_id, "is_favorited": True}


@router.delete("/favorites/{signal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_favorites(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    remove_favorite(db, user_id=user.id, signal_id=signal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/favorites", response_model=PaginatedSignals)
def get_favorites(
    limit: int = 24,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PaginatedSignals:
    user = _require_user(current_user)
    return list_signals(
        db=db,
        league=None,
        team=None,
        player=None,
        signal_type=None,
        limit=limit,
        before_id=None,
        current_user_id=user.id,
        favorited_only=True,
    )
