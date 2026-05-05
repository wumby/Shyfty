from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.shyft import FeedContextRead, PaginatedShyfts, ShyftRead, ShyftTraceRead
from app.services.comment_service import list_discussion_preview
from app.services.shyft_inspection_service import inspect_shyft
from app.services.shyft_service import (
    FEED_MODE_ALL,
    FEED_MODE_FOLLOWING,
    SORT_MODE_NEWEST,
    list_shyfts,
    list_trending_shyfts,
)

router = APIRouter()


@router.get("/shyfts/trending", response_model=list[ShyftRead])
def get_trending_signals(
    limit: int = 12,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[ShyftRead]:
    return list_trending_shyfts(
        db=db,
        limit=limit,
        current_user_id=current_user.id if current_user is not None else None,
    )


@router.get("/shyfts", response_model=PaginatedShyfts)
def get_signals(
    league: Optional[str] = None,
    team: Optional[str] = None,
    player: Optional[str] = None,
    shyft_type: Optional[str] = Query(default=None, alias="shyft_type"),
    sort: str = Query(default=SORT_MODE_NEWEST),
    feed: str = Query(default=FEED_MODE_ALL),
    limit: int = 24,
    before_id: Optional[int] = Query(default=None, alias="before_id"),
    date_from: Optional[date] = Query(default=None, alias="date_from"),
    date_to: Optional[date] = Query(default=None, alias="date_to"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PaginatedShyfts:
    return list_shyfts(
        db=db,
        league=league,
        team=team,
        player=player,
        shyft_type=shyft_type,
        limit=limit,
        before_id=before_id,
        current_user_id=current_user.id if current_user is not None else None,
        sort_mode=sort,
        feed_mode=feed,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/shyfts/following", response_model=PaginatedShyfts)
def get_following_signals(
    league: Optional[str] = None,
    shyft_type: Optional[str] = Query(default=None, alias="shyft_type"),
    sort: str = Query(default=SORT_MODE_NEWEST),
    limit: int = 24,
    before_id: Optional[int] = Query(default=None, alias="before_id"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PaginatedShyfts:
    return list_shyfts(
        db=db,
        league=league,
        shyft_type=shyft_type,
        limit=limit,
        before_id=before_id,
        current_user_id=current_user.id if current_user is not None else None,
        sort_mode=sort,
        feed_mode=FEED_MODE_FOLLOWING,
    )


@router.get("/shyfts/{shyft_id}", response_model=ShyftTraceRead)
def get_signal_detail(
    shyft_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ShyftTraceRead:
    trace = inspect_shyft(db, shyft_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Shyft not found")
    trace.discussion_preview = list_discussion_preview(
        db,
        shyft_id=shyft_id,
        current_user_id=current_user.id if current_user else None,
    )
    trace.feed_context = FeedContextRead(feed_mode=FEED_MODE_ALL, sort_mode=SORT_MODE_NEWEST)
    return trace
