"""Ingest pipeline: fetch → record raw events → normalize → generate shyfts.

Two entry points:
  - run_full_ingest: existing batch path; fetches all recent games, wipes and reloads,
    then regenerates all shyfts. Safe and predictable for daily scheduled runs.
  - run_incremental_ingest: event-oriented path; processes a list of IngestSource
    implementations (or individual game IDs), records RawIngestEvents for provenance,
    normalizes incrementally (idempotent), and regenerates shyfts only for
    affected players.
  - run_season_backfill: one-time backfill for a full prior season; uses incremental
    (no-wipe) path so existing data is never clobbered.

Future Kafka consumer plug-in point:
    Replace or supplement run_incremental_ingest with a long-running consumer that
    calls _process_source(db, source) in a loop. Each Kafka message becomes one
    IngestEvent, is written to raw_ingest_events, normalized, and triggers targeted
    shyft regeneration — all without touching unaffected players' data.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    games_fetched: int
    players_loaded: int
    stats_loaded: int
    shyfts_created: int
    shyfts_updated: int


def run_full_ingest(
    days_back: int = 21,
    max_games: int = 50,
    season: Optional[str] = None,
) -> IngestResult:
    """Full batch ingest: fetch → partial wipe → reload → regenerate all shyfts.

    Uses a partial wipe (clear_since = days_back ago) so prior-season backfill data
    is never clobbered. Called by the daily scheduler at 3 AM UTC.
    """
    from datetime import date, timedelta

    from app.db.session import SessionLocal
    from app.services.nba_ingest_service import fetch_recent_nba_data
    from app.services.nba_normalization_service import load_nba_snapshot
    from app.services.shyft_generation_service import generate_shyfts

    clear_since = date.today() - timedelta(days=days_back + 1)

    logger.info("Ingest: fetching NBA data (days_back=%d, max_games=%d)", days_back, max_games)
    fetch = fetch_recent_nba_data(season=season, days_back=days_back, max_games=max_games)
    logger.info("Ingest: fetched %d games, %d teams", fetch.game_count, fetch.team_count)

    with SessionLocal() as db:
        logger.info("Ingest: normalizing snapshot → DB (clear_since=%s)", clear_since)
        load = load_nba_snapshot(db, clear_since=clear_since)
        logger.info(
            "Ingest: loaded teams=%d players=%d games=%d player_stats=%d team_stats=%d",
            load.teams_loaded,
            load.players_loaded,
            load.games_loaded,
            load.stats_loaded,
            load.team_stats_loaded,
        )

        logger.info("Ingest: running shyft engine")
        sig = generate_shyfts(db)
        logger.info(
            "Ingest: shyfts created=%d updated=%d deleted=%d",
            sig.created_shyfts,
            sig.updated_shyfts,
            sig.deleted_shyfts,
        )

    return IngestResult(
        games_fetched=fetch.game_count,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        shyfts_created=sig.created_shyfts,
        shyfts_updated=sig.updated_shyfts,
    )


def _record_raw_ingest_events(db, events) -> None:
    """Write IngestEvents to raw_ingest_events, skipping already-seen external_ids."""
    from sqlalchemy import select
    from app.models.raw_ingest_event import RawIngestEvent

    for event in events:
        existing = db.execute(
            select(RawIngestEvent.id).where(
                RawIngestEvent.source == event.source,
                RawIngestEvent.external_id == event.external_id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            continue

        db.add(RawIngestEvent(
            source=event.source,
            source_type=event.source_type.value,
            external_id=event.external_id,
            event_timestamp=event.event_timestamp,
            ingested_at=event.ingested_at,
            raw_payload=json.dumps(event.raw_payload) if event.raw_payload else None,
            status="processed",
        ))
    db.flush()


def run_incremental_ingest(
    days_back: int = 21,
    max_games: int = 50,
    season: Optional[str] = None,
) -> IngestResult:
    """Incremental ingest: fetch → record raw events → idempotent normalize → targeted shyft regen.

    Unlike run_full_ingest, this path:
    - Does NOT wipe existing data before loading
    - Records each game as a RawIngestEvent before normalization
    - Skips player_game_stats rows that already exist (idempotent)
    - Regenerates shyfts only for players affected by new data

    Suitable for incremental runs (e.g., triggered by a webhook or event queue)
    and is the path a future Kafka consumer would use for real-time updates.

    Future Kafka consumer plug-in point:
        Replace the NBASAPISource fetch_events() call here with a Kafka consumer
        that yields one IngestEvent per message. Everything below — raw event
        recording, idempotent normalization, targeted shyft regeneration — is
        identical for stream and batch sources.
    """
    from app.db.session import SessionLocal
    from app.ingest.nba_source import NBASAPISource
    from app.services.shyft_generation_service import generate_shyfts_for_players

    source = NBASAPISource()
    logger.info(
        "Incremental ingest: fetching events from %s (days_back=%d, max_games=%d)",
        source.source_name, days_back, max_games,
    )

    events = list(source.fetch_events(season=season, days_back=days_back, max_games=max_games))
    logger.info("Incremental ingest: received %d game events", len(events))

    with SessionLocal() as db:
        _record_raw_ingest_events(db, events)
        logger.info("Incremental ingest: recorded %d raw ingest events", len(events))

        load = source.load_events(db, events)
        db.commit()
        logger.info(
            "Incremental ingest: loaded teams=%d players=%d games=%d stats=%d (skipped=%d)",
            load.teams_loaded,
            load.players_loaded,
            load.games_loaded,
            load.stats_loaded,
            load.skipped_stat_rows,
        )

        affected_player_ids = load.affected_player_ids
        affected_team_ids = load.affected_team_ids
        if affected_player_ids or affected_team_ids:
            logger.info(
                "Incremental ingest: regenerating shyfts for %d affected players and %d teams",
                len(affected_player_ids),
                len(affected_team_ids),
            )
            sig = generate_shyfts_for_players(db, affected_player_ids, team_ids=affected_team_ids)
        else:
            logger.info("Incremental ingest: no new player/team data, skipping shyft generation")
            from app.services.shyft_generation_service import ShyftGenerationResult
            sig = ShyftGenerationResult()

        logger.info(
            "Incremental ingest: shyfts created=%d updated=%d deleted=%d",
            sig.created_shyfts,
            sig.updated_shyfts,
            sig.deleted_shyfts,
        )

    return IngestResult(
        games_fetched=load.games_loaded,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        shyfts_created=sig.created_shyfts,
        shyfts_updated=sig.updated_shyfts,
    )


def run_season_backfill(
    season: str,
    *,
    max_games: int = 1300,
    sleep_between_games: float = 1.0,
) -> IngestResult:
    """One-time backfill for a full prior season.

    Uses the incremental (no-wipe) path — existing data is never clobbered.
    Fetches the entire season date range, then generates shyfts only for
    the newly affected players.

    Args:
        season: Season label like "2024-25".
        max_games: Upper bound on games fetched (1300 covers a full regular season).
        sleep_between_games: Seconds to sleep between per-game API calls; default 1.0
            keeps well within free-tier rate limits for a backfill run.
    """
    from app.db.session import SessionLocal
    from app.domain.seasons import season_date_range
    from app.services.nba_ingest_service import fetch_recent_nba_data
    from app.services.nba_normalization_service import load_nba_snapshot
    from app.services.shyft_generation_service import generate_shyfts_for_players

    date_from, date_to = season_date_range(season)
    logger.info(
        "Season backfill: fetching %s (%s → %s), max_games=%d, sleep=%.1fs",
        season, date_from, date_to, max_games, sleep_between_games,
    )

    fetch = fetch_recent_nba_data(
        season=season,
        date_from_override=date_from,
        date_to_override=date_to,
        max_games=max_games,
        sleep_between_games=sleep_between_games,
    )
    logger.info("Season backfill: fetched %d games, %d teams", fetch.game_count, fetch.team_count)

    with SessionLocal() as db:
        # Incremental load: no wipe, idempotent upserts
        load = load_nba_snapshot(db, clear_since=date_from)
        db.commit()
        logger.info(
            "Season backfill: loaded teams=%d players=%d games=%d stats=%d",
            load.teams_loaded,
            load.players_loaded,
            load.games_loaded,
            load.stats_loaded,
        )

        affected_player_ids = load.affected_player_ids
        affected_team_ids = load.affected_team_ids
        if affected_player_ids or affected_team_ids:
            logger.info(
                "Season backfill: regenerating shyfts for %d affected players and %d teams",
                len(affected_player_ids),
                len(affected_team_ids),
            )
            sig = generate_shyfts_for_players(db, affected_player_ids, team_ids=affected_team_ids)
        else:
            logger.info("Season backfill: no new player/team data, skipping shyft generation")
            from app.services.shyft_generation_service import ShyftGenerationResult
            sig = ShyftGenerationResult()

        logger.info(
            "Season backfill: shyfts created=%d updated=%d",
            sig.created_shyfts,
            sig.updated_shyfts,
        )

    return IngestResult(
        games_fetched=fetch.game_count,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        shyfts_created=sig.created_shyfts,
        shyfts_updated=sig.updated_shyfts,
    )
