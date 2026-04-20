from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: str
    team_name: str
    league_name: str
    is_followed: bool = False


class PlayerDetail(PlayerRead):
    signal_count: int


class MetricSeriesPoint(BaseModel):
    game_id: int
    game_date: date
    metrics: dict[str, float]


class GameLogRow(BaseModel):
    game_id: int
    game_date: date
    season: Optional[str] = None
    opponent: str
    home_away: str
    points: Optional[int] = None
    rebounds: Optional[int] = None
    assists: Optional[int] = None
    passing_yards: Optional[int] = None
    rushing_yards: Optional[int] = None
    receiving_yards: Optional[int] = None
    touchdowns: Optional[int] = None
    usage_rate: Optional[float] = None


class SeasonAveragesRow(BaseModel):
    season: str
    games_played: int
    points: Optional[float] = None
    rebounds: Optional[float] = None
    assists: Optional[float] = None
    passing_yards: Optional[float] = None
    rushing_yards: Optional[float] = None
    receiving_yards: Optional[float] = None
    touchdowns: Optional[float] = None
    usage_rate: Optional[float] = None
