from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.signal import PaginatedSignals, SignalRead
from app.services.signal_service import list_signals, list_trending_signals

router = APIRouter()


@router.get("/signals/trending", response_model=list[SignalRead])
def get_trending_signals(
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[SignalRead]:
    return list_trending_signals(
        db=db,
        limit=limit,
        current_user_id=current_user.id if current_user is not None else None,
    )


@router.get("/signals", response_model=PaginatedSignals)
def get_signals(
    league: Optional[str] = None,
    team: Optional[str] = None,
    player: Optional[str] = None,
    signal_type: Optional[str] = Query(default=None, alias="signal_type"),
    limit: int = 24,
    before_id: Optional[int] = Query(default=None, alias="before_id"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PaginatedSignals:
    return list_signals(
        db=db,
        league=league,
        team=team,
        player=player,
        signal_type=signal_type,
        limit=limit,
        before_id=before_id,
        current_user_id=current_user.id if current_user is not None else None,
    )
