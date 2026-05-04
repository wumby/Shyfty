from __future__ import annotations

from datetime import date

from app.ingest.providers import ProviderGame, ProviderGameDetail


class NFLScheduleProvider:
    league = "nfl"

    def discover_schedule(self, *, start_date: date, end_date: date) -> list[ProviderGame]:
        raise NotImplementedError("NFL schedule provider is not implemented yet.")

    def fetch_game_detail(self, external_game_id: str) -> ProviderGameDetail:
        raise NotImplementedError("NFL detail provider is not implemented yet.")
