"""NBA Stats API ingest source.

Implements IngestSource for the NBA Stats API (polled batch, source_type=API).
Wraps the existing fetch and incremental normalization services.

Each game's combined boxscore (traditional + advanced + usage) is treated as one IngestEvent,
matching the granularity a Kafka producer would use if this data were streamed.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from app.ingest.base import IngestEvent, IngestSource, LoadSummary, SourceType
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM, fetch_recent_nba_data, raw_nba_root

logger = logging.getLogger(__name__)


class NBASAPISource(IngestSource):
    """NBA Stats API batch ingest source.

    Fetches game data via the NBA Stats API, writes raw JSON snapshots to disk,
    then loads each game incrementally into the DB with idempotency checks.

    Future Kafka analog: a KafkaNBABoxscoreSource would implement the same interface
    but consume from a Kafka topic instead of polling the REST API. The load_events()
    implementation would be identical.
    """

    @property
    def source_name(self) -> str:
        return NBA_SOURCE_SYSTEM

    @property
    def source_type(self) -> SourceType:
        return SourceType.API

    def fetch_events(
        self,
        *,
        season: Optional[str] = None,
        days_back: int = 21,
        max_games: int = 50,
        **kwargs,
    ) -> Iterator[IngestEvent]:
        """Fetch recent NBA games and yield one IngestEvent per game.

        Writes raw JSON snapshots to disk as a side effect (existing behavior).
        Each yielded event carries the merged traditional + advanced + usage boxscore payload
        for one game — matching the message granularity a Kafka producer would use.
        """
        fetch_result = fetch_recent_nba_data(season=season, days_back=days_back, max_games=max_games)
        snapshot_dir = fetch_result.output_dir

        import json as _json
        from pathlib import Path as _Path

        manifest_path = snapshot_dir / "manifest.json"
        manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))

        for game_id in manifest["game_ids"]:
            traditional_path = snapshot_dir / "games" / f"{game_id}_traditional.json"
            advanced_path = snapshot_dir / "games" / f"{game_id}_advanced.json"
            usage_path = snapshot_dir / "games" / f"{game_id}_usage.json"
            if not traditional_path.exists():
                continue

            raw_payload: dict[str, Any] = {
                "source_system": NBA_SOURCE_SYSTEM,
                "game_id": game_id,
                "snapshot_dir": str(snapshot_dir),
                "traditional": _json.loads(traditional_path.read_text(encoding="utf-8")),
                "advanced": _json.loads(advanced_path.read_text(encoding="utf-8")) if advanced_path.exists() else {},
                "usage": _json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.exists() else {},
            }

            yield IngestEvent(
                source=self.source_name,
                source_type=self.source_type,
                external_id=str(game_id),
                event_timestamp=None,  # resolved from boxscore during normalization
                ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
                raw_payload=raw_payload,
            )

    def load_events(self, db: Session, events: list[IngestEvent]) -> LoadSummary:
        """Normalize and incrementally load a batch of NBA game events.

        Idempotent: skips player_game_stats rows that already exist for the same
        (source_system, source_game_id, source_player_id). Does not wipe existing data.
        """
        from app.services.nba_normalization_service import load_nba_games_incremental

        game_payloads = [e.raw_payload for e in events]
        result = load_nba_games_incremental(db, game_payloads=game_payloads)
        return LoadSummary(
            teams_loaded=result.teams_loaded,
            players_loaded=result.players_loaded,
            games_loaded=result.games_loaded,
            stats_loaded=result.stats_loaded,
            skipped_stat_rows=result.skipped_stat_rows,
            affected_player_ids=result.affected_player_ids,
        )
