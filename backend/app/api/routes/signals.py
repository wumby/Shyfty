from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.signal import FeedContextRead, PaginatedSignals, SignalRead, SignalTraceRead
from app.services.comment_service import list_discussion_preview
from app.services.signal_inspection_service import inspect_signal
from app.services.signal_service import (
    FEED_MODE_ALL,
    FEED_MODE_FOLLOWING,
    SORT_MODE_NEWEST,
    list_signals,
    list_trending_signals,
)

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
    sort: str = Query(default=SORT_MODE_NEWEST),
    feed: str = Query(default=FEED_MODE_ALL),
    limit: int = 24,
    before_id: Optional[int] = Query(default=None, alias="before_id"),
    date_from: Optional[date] = Query(default=None, alias="date_from"),
    date_to: Optional[date] = Query(default=None, alias="date_to"),
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
        sort_mode=sort,
        feed_mode=feed,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/signals/following", response_model=PaginatedSignals)
def get_following_signals(
    league: Optional[str] = None,
    signal_type: Optional[str] = Query(default=None, alias="signal_type"),
    sort: str = Query(default=SORT_MODE_NEWEST),
    limit: int = 24,
    before_id: Optional[int] = Query(default=None, alias="before_id"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PaginatedSignals:
    return list_signals(
        db=db,
        league=league,
        signal_type=signal_type,
        limit=limit,
        before_id=before_id,
        current_user_id=current_user.id if current_user is not None else None,
        sort_mode=sort,
        feed_mode=FEED_MODE_FOLLOWING,
    )


@router.get("/signals/{signal_id}", response_model=SignalTraceRead)
def get_signal_detail(
    signal_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> SignalTraceRead:
    trace = inspect_signal(db, signal_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Signal not found")
    trace.discussion_preview = list_discussion_preview(
        db,
        signal_id=signal_id,
        current_user_id=current_user.id if current_user else None,
    )
    trace.feed_context = FeedContextRead(feed_mode=FEED_MODE_ALL, sort_mode=SORT_MODE_NEWEST)
    return trace
