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

MIN_BOOTSTRAP_GAMES_PER_LEAGUE = 90
MIN_INCREMENTAL_GAMES_PER_LEAGUE = 30
MIN_NFL_COMPLETED_WEEKS = 5
MIN_NBA_GAMES_PER_TEAM = 5


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
    failed: bool = False
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

    @property
    def failed_sources(self) -> tuple[SourceSyncResult, ...]:
        return tuple(result for result in self.source_results if result.failed)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_sources)


def get_default_sync_sources() -> tuple[str, ...]:
    sources: list[str] = []
    if settings.enable_nba_sync:
        sources.append("nba")
    if settings.enable_nfl_sync:
        sources.append("nfl")
    return tuple(sources)


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


def _existing_external_ids(db, *, source: str) -> set[str]:
    rows = db.execute(
        select(RawIngestEvent.external_id).where(RawIngestEvent.source == source)
    ).scalars().all()
    return {row for row in rows if row}


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
    from app.services.schedule_sync_service import sync_league
    result = sync_league(league="nba", force=(mode == "bootstrap"))
    with SessionLocal() as db:
        processed_at = datetime.utcnow()
        _upsert_checkpoint(
            db,
            source="nba",
            checkpoint_key=f"{mode}_last_success",
            checkpoint_value=processed_at.isoformat(),
            checkpoint_metadata={
                "days_back": days_back,
                "max_games": max_games,
                "season": season,
                "games_discovered": result.discovered_games,
                "games_hydrated": result.hydrated_games,
                "players_loaded": result.players_loaded,
                "stats_loaded": result.player_stats_loaded,
            },
        )
        db.commit()

    return SourceSyncResult(
        source="nba",
        mode=mode,
        games_fetched=result.hydrated_games,
        players_loaded=result.players_loaded,
        stats_loaded=result.player_stats_loaded,
        signals_created=result.signals_created,
        signals_updated=result.signals_updated,
    )


def _run_nfl_sync(
    *,
    mode: SyncMode,
    max_games: int,
    season: Optional[str],
) -> SourceSyncResult:
    if not settings.enable_nfl_sync:
        return SourceSyncResult(
            source="nfl",
            mode=mode,
            skipped=True,
            detail="NFL sync disabled by ENABLE_NFL_SYNC=false",
        )

    from app.services.schedule_sync_service import sync_league
    result = sync_league(league="nfl", force=(mode == "bootstrap"))

    return SourceSyncResult(
        source="nfl",
        mode=mode,
        games_fetched=result.hydrated_games,
        players_loaded=result.players_loaded,
        stats_loaded=result.player_stats_loaded,
        signals_created=result.signals_created,
        signals_updated=result.signals_updated,
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
        try:
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
        except Exception as exc:
            logger.exception("Sync source failed: %s", source)
            results.append(
                SourceSyncResult(
                    source=source,
                    mode=mode,
                    skipped=True,
                    failed=True,
                    detail=f"failed: {exc}",
                )
            )

    return SyncResult(mode=mode, source_results=tuple(results))
