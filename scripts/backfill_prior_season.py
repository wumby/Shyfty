#!/usr/bin/env python3
"""Backfill one full prior NBA season into the Shyfty DB.

Usage:
    python scripts/backfill_prior_season.py [season]

    season: optional, e.g. "2024-25". Defaults to the season before the current one.

This uses the incremental (no-wipe) path so existing data is never clobbered.
Rate-limits API calls to ~1 req/s to stay within free-tier limits.
A full regular season is ~1230 games; expect ~25–30 minutes at 1 req/s.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend src is on the path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.domain.seasons import prior_season, season_from_date
from datetime import date


def main() -> None:
    if len(sys.argv) > 1:
        season = sys.argv[1]
    else:
        season = prior_season(season_from_date(date.today()))

    print(f"Backfilling season: {season}")
    print("This will take ~25–30 minutes at 1 req/s rate limit.")
    print("Press Ctrl+C to abort.\n")

    from app.services.ingest_pipeline import run_season_backfill

    result = run_season_backfill(season, max_games=1300, sleep_between_games=1.0)
    print(
        f"\nBackfill complete:\n"
        f"  Games fetched:   {result.games_fetched}\n"
        f"  Players loaded:  {result.players_loaded}\n"
        f"  Stats loaded:    {result.stats_loaded}\n"
        f"  Signals created: {result.signals_created}\n"
        f"  Signals updated: {result.signals_updated}\n"
    )


if __name__ == "__main__":
    main()
