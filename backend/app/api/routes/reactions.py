from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.reaction import EmojiReactionWrite, ReactionRead, ReactionWrite
from app.services.abuse_service import enforce_rate_limit
from app.services.reaction_service import ReactionLimitError, remove_signal_reaction, set_signal_reaction

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.put("/signals/{signal_id}/reaction", response_model=ReactionRead)
def put_signal_reaction(
    signal_id: int,
    payload: ReactionWrite,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ReactionRead:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    try:
        reaction = set_signal_reaction(db, signal_id=signal_id, user_id=user.id, reaction_type=payload.type)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReactionLimitError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ReactionRead(
        id=reaction.id,
        signal_id=reaction.signal_id,
        user_id=reaction.user_id,
        emoji=reaction.type,
        created_at=reaction.created_at,
        updated_at=reaction.updated_at,
    )


@router.delete("/signals/{signal_id}/reaction", status_code=status.HTTP_204_NO_CONTENT)
def delete_signal_reaction(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    # Legacy clear keeps old behavior and clears all of the caller's reactions on this signal.
    for fallback in ("agree", "strong", "risky"):
        remove_signal_reaction(db, signal_id=signal_id, user_id=user.id, emoji=fallback)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/signals/{signal_id}/reactions", response_model=ReactionRead)
def post_signal_reaction(
    signal_id: int,
    payload: EmojiReactionWrite,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ReactionRead:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    try:
        reaction = set_signal_reaction(db, signal_id=signal_id, user_id=user.id, emoji=payload.emoji)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ReactionLimitError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ReactionRead(
        id=reaction.id,
        signal_id=reaction.signal_id,
        user_id=reaction.user_id,
        emoji=reaction.type,
        created_at=reaction.created_at,
        updated_at=reaction.updated_at,
    )


@router.delete("/signals/{signal_id}/reactions/{emoji}", status_code=status.HTTP_204_NO_CONTENT)
def delete_signal_reaction_by_emoji(
    signal_id: int,
    emoji: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    remove_signal_reaction(db, signal_id=signal_id, user_id=user.id, emoji=emoji)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
