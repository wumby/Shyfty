from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.schemas.player import MetricSeriesPoint, PlayerDetail, PlayerRead
from app.schemas.signal import SignalRead
from app.services.player_service import (
    get_player_detail,
    get_player_metric_series,
    get_player_signals,
    list_players,
)

router = APIRouter()


@router.get("/players", response_model=list[PlayerRead])
def get_players(db: Session = Depends(get_db)) -> list[PlayerRead]:
    return list_players(db)


@router.get("/players/{player_id}", response_model=PlayerDetail)
def get_player(player_id: int, db: Session = Depends(get_db)) -> PlayerDetail:
    player = get_player_detail(db, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/players/{player_id}/signals", response_model=list[SignalRead])
def get_player_signal_feed(player_id: int, db: Session = Depends(get_db)) -> list[SignalRead]:
    return get_player_signals(db, player_id)


@router.get("/players/{player_id}/metrics", response_model=list[MetricSeriesPoint])
def get_player_metrics(player_id: int, db: Session = Depends(get_db)) -> list[MetricSeriesPoint]:
    return get_player_metric_series(db, player_id)

