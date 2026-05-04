from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional, Protocol


@dataclass(frozen=True)
class ProviderGame:
    league: str
    external_game_id: str
    game_date: date
    status: str
    home_team_external_id: str
    away_team_external_id: str
    source_updated_at: Optional[datetime] = None
    raw_payload: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderGameDetail:
    game: ProviderGame
    payload: dict


class LeagueProvider(Protocol):
    league: str

    def discover_schedule(self, *, start_date: date, end_date: date) -> list[ProviderGame]:
        ...

    def fetch_game_detail(self, external_game_id: str) -> ProviderGameDetail:
        ...
