from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Literal, Optional

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.game import Game
from app.models.raw_ingest_event import RawIngestEvent
from app.models.sync_checkpoint import SyncCheckpoint

logger = logging.getLogger(__name__)

SyncMode = Literal["bootstrap", "incremental"]

MIN_LAST_FIVE_GAMES_PER_LEAGUE = 90
MIN_NFL_COMPLETED_WEEKS = 5


@dataclass(frozen=True)
class SourceSyncResult:
    source: str
    mode: SyncMode
    games_fetched: int = 0
    players_loaded: int = 0
    stats_loaded: int = 0
    signals_created: int = 0
    signals_updated: int = 0
    skipped: bool = False
    detail: Optional[str] = None


@dataclass(frozen=True)
class SyncResult:
    mode: SyncMode
    source_results: tuple[SourceSyncResult, ...] = field(default_factory=tuple)

    @property
    def games_fetched(self) -> int:
        return sum(result.games_fetched for result in self.source_results)

    @property
    def players_loaded(self) -> int:
        return sum(result.players_loaded for result in self.source_results)

    @property
    def stats_loaded(self) -> int:
        return sum(result.stats_loaded for result in self.source_results)

    @property
    def signals_created(self) -> int:
        return sum(result.signals_created for result in self.source_results)

    @property
    def signals_updated(self) -> int:
        return sum(result.signals_updated for result in self.source_results)


def get_default_sync_sources() -> tuple[str, ...]:
    return ("nba", "nfl")


def _record_raw_ingest_events(db, events) -> None:
    for event in events:
        existing = db.execute(
            select(RawIngestEvent.id).where(
                RawIngestEvent.source == event.source,
                RawIngestEvent.external_id == event.external_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue

        db.add(
            RawIngestEvent(
                source=event.source,
                source_type=event.source_type.value,
                external_id=event.external_id,
                event_timestamp=event.event_timestamp,
                ingested_at=event.ingested_at,
                raw_payload=json.dumps(event.raw_payload) if event.raw_payload else None,
                status="processed",
            )
        )
    db.flush()


def _upsert_checkpoint(
    db,
    *,
    source: str,
    checkpoint_key: str,
    checkpoint_value: Optional[str],
    checkpoint_metadata: Optional[dict],
) -> None:
    checkpoint = db.execute(
        select(SyncCheckpoint).where(
            SyncCheckpoint.source == source,
            SyncCheckpoint.checkpoint_key == checkpoint_key,
        )
    ).scalar_one_or_none()

    if checkpoint is None:
        checkpoint = SyncCheckpoint(source=source, checkpoint_key=checkpoint_key)
        db.add(checkpoint)

    checkpoint.checkpoint_value = checkpoint_value
    checkpoint.checkpoint_metadata = json.dumps(checkpoint_metadata) if checkpoint_metadata is not None else None
    checkpoint.updated_at = datetime.utcnow()
    db.flush()


def _mark_games_processed(db, game_ids: Iterable[int], processed_at: datetime) -> None:
    for game_id in set(game_ids):
        game = db.get(Game, game_id)
        if game is None:
            continue
        game.last_synced_at = processed_at
        game.signals_generated_at = processed_at
    db.flush()


def _run_nba_sync(
    *,
    mode: SyncMode,
    days_back: int,
    max_games: int,
    season: Optional[str],
) -> SourceSyncResult:
    from app.ingest.nba_source import NBASAPISource
    from app.services.signal_generation_service import SignalGenerationResult, generate_signals_for_players

    source = NBASAPISource()
    max_games = max(max_games, MIN_LAST_FIVE_GAMES_PER_LEAGUE)
    logger.info("Sync: starting %s sync for source=%s", mode, source.source_name)
    events = list(source.fetch_events(season=season, days_back=days_back, max_games=max_games))

    with SessionLocal() as db:
        _record_raw_ingest_events(db, events)
        load = source.load_events(db, events)

        affected_player_ids = load.affected_player_ids
        affected_team_ids = load.affected_team_ids
        if affected_player_ids or affected_team_ids:
            sig = generate_signals_for_players(db, affected_player_ids, team_ids=affected_team_ids)
        else:
            sig = SignalGenerationResult()

        processed_at = datetime.utcnow()
        _mark_games_processed(db, load.affected_game_ids, processed_at)
        _upsert_checkpoint(
            db,
            source="nba",
            checkpoint_key=f"{mode}_last_success",
            checkpoint_value=processed_at.isoformat(),
            checkpoint_metadata={
                "days_back": days_back,
                "max_games": max_games,
                "season": season,
                "games_loaded": load.games_loaded,
                "players_loaded": load.players_loaded,
                "stats_loaded": load.stats_loaded,
                "skipped_stat_rows": load.skipped_stat_rows,
            },
        )
        db.commit()

    return SourceSyncResult(
        source="nba",
        mode=mode,
        games_fetched=load.games_loaded,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        signals_created=sig.created_signals,
        signals_updated=sig.updated_signals,
    )


def _run_nfl_sync(
    *,
    mode: SyncMode,
    max_games: int,
    season: Optional[str],
) -> SourceSyncResult:
    from app.ingest.nfl_source import ESPNNFLSource
    from app.services.signal_generation_service import SignalGenerationResult, generate_signals_for_players

    source = ESPNNFLSource()
    weeks_back = max(
        settings.espn_nfl_bootstrap_weeks if mode == "bootstrap" else settings.espn_nfl_incremental_weeks,
        MIN_NFL_COMPLETED_WEEKS,
    )
    max_games = max(max_games, MIN_LAST_FIVE_GAMES_PER_LEAGUE)

    logger.info("Sync: starting %s sync for source=%s", mode, source.source_name)
    events = list(source.fetch_events(season=season, max_games=max_games, weeks_back=weeks_back))

    with SessionLocal() as db:
        _record_raw_ingest_events(db, events)
        load = source.load_events(db, events)

        affected_player_ids = load.affected_player_ids
        affected_team_ids = load.affected_team_ids
        if affected_player_ids or affected_team_ids:
            sig = generate_signals_for_players(db, affected_player_ids, team_ids=affected_team_ids)
        else:
            sig = SignalGenerationResult()

        processed_at = datetime.utcnow()
        _mark_games_processed(db, load.affected_game_ids, processed_at)
        _upsert_checkpoint(
            db,
            source="nfl",
            checkpoint_key=f"{mode}_last_success",
            checkpoint_value=processed_at.isoformat(),
            checkpoint_metadata={
                "weeks_back": weeks_back,
                "max_games": max_games,
                "season": season,
                "games_loaded": load.games_loaded,
                "players_loaded": load.players_loaded,
                "stats_loaded": load.stats_loaded,
                "skipped_stat_rows": load.skipped_stat_rows,
                "windows": source.last_windows,
            },
        )
        db.commit()

    return SourceSyncResult(
        source="nfl",
        mode=mode,
        games_fetched=load.games_loaded,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        signals_created=sig.created_signals,
        signals_updated=sig.updated_signals,
        detail=(
            ", ".join(f"{window['season']}-W{window['week']}" for window in source.last_windows)
            if source.last_windows
            else "No completed NFL windows returned by ESPN."
        ),
    )


def run_sync(
    *,
    mode: SyncMode = "incremental",
    sources: Optional[tuple[str, ...]] = None,
    days_back: Optional[int] = None,
    max_games: int = 50,
    season: Optional[str] = None,
) -> SyncResult:
    resolved_sources = sources or get_default_sync_sources()
    normalized_sources = tuple(dict.fromkeys(source.lower() for source in resolved_sources))
    resolved_days_back = days_back if days_back is not None else (30 if mode == "bootstrap" else 7)
    results: list[SourceSyncResult] = []

    for source in normalized_sources:
        if source == "nba":
            results.append(
                _run_nba_sync(
                    mode=mode,
                    days_back=resolved_days_back,
                    max_games=max_games,
                    season=season,
                )
            )
            continue

        if source == "nfl":
            results.append(
                _run_nfl_sync(
                    mode=mode,
                    max_games=max_games,
                    season=season,
                )
            )
            continue

        raise ValueError(f"Unsupported sync source: {source}")

    return SyncResult(mode=mode, source_results=tuple(results))
