"""Unified NBA ingest pipeline: fetch → normalize → generate signals."""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestResult:
    games_fetched: int
    players_loaded: int
    stats_loaded: int
    signals_created: int
    signals_updated: int


def run_full_ingest(
    days_back: int = 21,
    max_games: int = 30,
    season: str | None = None,
) -> IngestResult:
    from app.db.session import SessionLocal
    from app.services.nba_ingest_service import fetch_recent_nba_data
    from app.services.nba_normalization_service import load_nba_snapshot
    from app.services.signal_generation_service import generate_signals

    logger.info("Ingest: fetching NBA data (days_back=%d, max_games=%d)", days_back, max_games)
    fetch = fetch_recent_nba_data(season=season, days_back=days_back, max_games=max_games)
    logger.info("Ingest: fetched %d games, %d teams", fetch.game_count, fetch.team_count)

    with SessionLocal() as db:
        logger.info("Ingest: normalizing snapshot → DB")
        load = load_nba_snapshot(db)
        logger.info(
            "Ingest: loaded teams=%d players=%d games=%d stats=%d",
            load.teams_loaded,
            load.players_loaded,
            load.games_loaded,
            load.stats_loaded,
        )

        logger.info("Ingest: running signal engine")
        sig = generate_signals(db)
        logger.info(
            "Ingest: signals created=%d updated=%d deleted=%d",
            sig.created_signals,
            sig.updated_signals,
            sig.deleted_signals,
        )

    return IngestResult(
        games_fetched=fetch.game_count,
        players_loaded=load.players_loaded,
        stats_loaded=load.stats_loaded,
        signals_created=sig.created_signals,
        signals_updated=sig.updated_signals,
    )
