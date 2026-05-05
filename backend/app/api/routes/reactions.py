from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.reaction import ReactionRead, ReactionWrite, ShyftReaction
from app.services.abuse_service import enforce_rate_limit
from app.services.reaction_service import remove_shyft_reaction, set_shyft_reaction

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.put("/shyfts/{shyft_id}/reaction", response_model=ReactionRead)
def put_signal_reaction(
    shyft_id: int,
    payload: ReactionWrite,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ReactionRead:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    try:
        reaction = set_shyft_reaction(db, shyft_id=shyft_id, user_id=user.id, reaction_type=payload.type.value)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    return ReactionRead(
        id=reaction.id,
        shyft_id=reaction.shyft_id,
        user_id=reaction.user_id,
        type=ShyftReaction(reaction.type),
        created_at=reaction.created_at,
        updated_at=reaction.updated_at,
    )


@router.delete("/shyfts/{shyft_id}/reaction", status_code=status.HTTP_204_NO_CONTENT)
def delete_signal_reaction(
    shyft_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    enforce_rate_limit(f"user:{user.id}", "reaction_write", limit=60, per_seconds=300)
    remove_shyft_reaction(db, shyft_id=shyft_id, user_id=user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
