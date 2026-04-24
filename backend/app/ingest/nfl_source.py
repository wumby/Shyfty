from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.ingest.base import IngestEvent, IngestSource, LoadSummary, SourceType
from app.services.nfl_ingest_service import NFL_SOURCE_SYSTEM, ESPNNFLClient


def _parse_season_year(raw: Optional[str]) -> Optional[int]:
    if not raw:
        return None
    raw = raw.strip()
    if "-" in raw:
        raw = raw.split("-", 1)[0]
    try:
        return int(raw)
    except ValueError:
        return None


class ESPNNFLSource(IngestSource):
    def __init__(self) -> None:
        self._last_teams: list[dict[str, Any]] = []
        self._last_windows: list[dict[str, int]] = []

    @property
    def source_name(self) -> str:
        return NFL_SOURCE_SYSTEM

    @property
    def source_type(self) -> SourceType:
        return SourceType.API

    @property
    def last_windows(self) -> list[dict[str, int]]:
        return list(self._last_windows)

    def fetch_events(
        self,
        *,
        season: Optional[str] = None,
        max_games: int = 80,
        weeks_back: Optional[int] = None,
        **kwargs,
    ) -> Iterator[IngestEvent]:
        client = ESPNNFLClient(timeout_seconds=settings.espn_timeout_seconds)
        resolved_weeks_back = weeks_back or settings.espn_nfl_incremental_weeks
        fetch = client.fetch_recent_completed_data(
            season=_parse_season_year(season),
            weeks_back=resolved_weeks_back,
            max_games=max_games,
        )
        self._last_teams = fetch.teams
        self._last_windows = [
            {"season": window.season, "week": window.week} for window in fetch.windows
        ]

        for index, boxscore in enumerate(fetch.boxscores):
            game_id = str(boxscore.get("GameID") or f"espn-nfl-{index}")
            event_date = boxscore.get("Date")
            yield IngestEvent(
                source=self.source_name,
                source_type=self.source_type,
                external_id=game_id,
                event_timestamp=(
                    datetime.fromisoformat(str(event_date).replace("Z", "+00:00"))
                    .astimezone(timezone.utc)
                    .replace(tzinfo=None)
                    if event_date
                    else None
                ),
                ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
                raw_payload=boxscore,
            )

    def load_events(self, db: Session, events: list[IngestEvent]) -> LoadSummary:
        from app.services.nfl_normalization_service import load_nfl_boxscores_incremental

        result = load_nfl_boxscores_incremental(
            db,
            teams_payload=self._last_teams,
            players_payload=[],
            boxscore_payloads=[event.raw_payload for event in events],
        )
        return LoadSummary(
            teams_loaded=result.teams_loaded,
            players_loaded=result.players_loaded,
            games_loaded=result.games_loaded,
            stats_loaded=result.stats_loaded,
            skipped_stat_rows=result.skipped_stat_rows,
            affected_player_ids=result.affected_player_ids,
            affected_team_ids=result.affected_team_ids,
            affected_game_ids=result.affected_game_ids,
        )
