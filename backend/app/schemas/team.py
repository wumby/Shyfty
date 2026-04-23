from pydantic import BaseModel

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
