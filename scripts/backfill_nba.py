#!/usr/bin/env python
"""Backfill historical NBA data — fetches up to 60 days back and regenerates all signals.

Usage:
    DATABASE_URL=sqlite:////path/to/shyfty.db python scripts/backfill_nba.py
    DATABASE_URL=sqlite:////path/to/shyfty.db python scripts/backfill_nba.py --days-back 60 --max-games 80
"""
import sys
from pathlib import Path

# Ensure the backend package is on the path when run from project root
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import argparse

from app.services.ingest_pipeline import run_full_ingest


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill historical NBA data + regenerate signals.")
    parser.add_argument("--days-back", type=int, default=60, help="Number of days to look back (default 60)")
    parser.add_argument("--max-games", type=int, default=80, help="Max games to fetch (default 80)")
    parser.add_argument("--season", default=None, help="NBA season string, e.g. 2024-25")
    args = parser.parse_args()

    print(f"Starting backfill: days_back={args.days_back} max_games={args.max_games}")
    result = run_full_ingest(
        days_back=args.days_back,
        max_games=args.max_games,
        season=args.season,
    )
    print(
        f"Backfill complete:\n"
        f"  Games fetched:    {result.games_fetched}\n"
        f"  Players loaded:   {result.players_loaded}\n"
        f"  Stats loaded:     {result.stats_loaded}\n"
        f"  Signals created:  {result.signals_created}\n"
        f"  Signals updated:  {result.signals_updated}\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
