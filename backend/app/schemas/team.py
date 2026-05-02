from pydantic import BaseModel
from datetime import date
from typing import Optional

from app.schemas.player import PlayerRead
from app.schemas.signal import SignalRead


class TeamRead(BaseModel):
    id: int
    name: str
    league_name: str
    player_count: int
    signal_count: int = 0
    is_followed: bool = False


class TeamDetail(TeamRead):
    players: list[PlayerRead]
    recent_signals: list[SignalRead]
    recent_box_scores: list["TeamBoxScore"] = []


class TeamBoxScore(BaseModel):
    game_id: int
    game_date: date
    season: Optional[str] = None
    opponent: str
    home_away: str
    points: Optional[int] = None
    rebounds: Optional[int] = None
    assists: Optional[int] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    turnovers: Optional[int] = None
    pace: Optional[float] = None
    off_rating: Optional[float] = None
    total_yards: Optional[int] = None
    first_downs: Optional[int] = None
    penalties: Optional[int] = None
    penalty_yards: Optional[int] = None
    turnovers_forced: Optional[int] = None
    turnovers_lost: Optional[int] = None
    third_down_pct: Optional[float] = None
    redzone_pct: Optional[float] = None
