from datetime import date

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
