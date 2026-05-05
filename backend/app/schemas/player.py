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
    shyft_count: int
    recent_box_scores: list["PlayerBoxScore"] = []


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
    passing_completions: Optional[int] = None
    passing_attempts: Optional[int] = None
    interceptions: Optional[int] = None
    rushing_yards: Optional[int] = None
    rushing_attempts: Optional[int] = None
    receiving_yards: Optional[int] = None
    receptions: Optional[int] = None
    targets: Optional[int] = None
    touchdowns: Optional[int] = None
    sacks: Optional[int] = None
    fumbles_lost: Optional[int] = None
    usage_rate: Optional[float] = None


class PlayerBoxScore(BaseModel):
    game_id: int
    game_date: date
    season: Optional[str] = None
    opponent: str
    home_away: str
    team_score: Optional[int] = None
    opponent_score: Optional[int] = None
    result: Optional[str] = None
    points: Optional[int] = None
    rebounds: Optional[int] = None
    assists: Optional[int] = None
    passing_yards: Optional[int] = None
    passing_completions: Optional[int] = None
    passing_attempts: Optional[int] = None
    interceptions: Optional[int] = None
    rushing_yards: Optional[int] = None
    rushing_attempts: Optional[int] = None
    receiving_yards: Optional[int] = None
    receptions: Optional[int] = None
    targets: Optional[int] = None
    touchdowns: Optional[int] = None
    sacks: Optional[int] = None
    fumbles_lost: Optional[int] = None
    usage_rate: Optional[float] = None
    steals: Optional[int] = None
    blocks: Optional[int] = None
    turnovers: Optional[int] = None
    minutes_played: Optional[float] = None
    plus_minus: Optional[int] = None
    fg_pct: Optional[float] = None
    fg3_pct: Optional[float] = None
    ft_pct: Optional[float] = None


class SeasonAveragesRow(BaseModel):
    season: str
    games_played: int
    points: Optional[float] = None
    rebounds: Optional[float] = None
    assists: Optional[float] = None
    passing_yards: Optional[float] = None
    passing_completions: Optional[float] = None
    passing_attempts: Optional[float] = None
    interceptions: Optional[float] = None
    rushing_yards: Optional[float] = None
    rushing_attempts: Optional[float] = None
    receiving_yards: Optional[float] = None
    receptions: Optional[float] = None
    targets: Optional[float] = None
    touchdowns: Optional[float] = None
    sacks: Optional[float] = None
    fumbles_lost: Optional[float] = None
    usage_rate: Optional[float] = None
