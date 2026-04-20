from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.player import GameLogRow, MetricSeriesPoint, PlayerDetail, PlayerRead, SeasonAveragesRow
from app.schemas.signal import SignalRead
from app.services.player_service import (
    get_player_detail,
    get_player_gamelog,
    get_player_metric_series,
    get_player_season_averages,
    get_player_signals,
    list_players,
)

router = APIRouter()


@router.get("/players", response_model=list[PlayerRead])
def get_players(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> list[PlayerRead]:
    return list_players(db, current_user_id=current_user.id if current_user else None)


@router.get("/players/{player_id}", response_model=PlayerDetail)
def get_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> PlayerDetail:
    player = get_player_detail(db, player_id, current_user_id=current_user.id if current_user else None)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/players/{player_id}/signals", response_model=list[SignalRead])
def get_player_signal_feed(player_id: int, db: Session = Depends(get_db)) -> list[SignalRead]:
    return get_player_signals(db, player_id)


@router.get("/players/{player_id}/gamelog", response_model=list[GameLogRow])
def get_player_gamelog_route(
    player_id: int,
    season: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> list[GameLogRow]:
    return get_player_gamelog(db, player_id, season=season)


@router.get("/players/{player_id}/season-averages", response_model=list[SeasonAveragesRow])
def get_player_season_averages_route(
    player_id: int,
    db: Session = Depends(get_db),
) -> list[SeasonAveragesRow]:
    return get_player_season_averages(db, player_id)


@router.get("/players/{player_id}/metrics", response_model=list[MetricSeriesPoint])
def get_player_metrics(player_id: int, db: Session = Depends(get_db)) -> list[MetricSeriesPoint]:
    return get_player_metric_series(db, player_id)
