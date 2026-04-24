"""Unified sync CLI: bootstrap or incrementally sync real provider data."""
import argparse

from app.services.sync_service import get_default_sync_sources, run_sync


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a real-data sync pipeline.")
    parser.add_argument("--mode", choices=["bootstrap", "incremental"], default="incremental")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Repeat to sync multiple sources. Defaults to nba and nfl.",
    )
    parser.add_argument("--days-back", type=int, default=None)
    parser.add_argument("--max-games", type=int, default=50)
    parser.add_argument("--season", default=None, help="e.g. 2024-25")
    args = parser.parse_args()

    result = run_sync(
        mode=args.mode,
        sources=tuple(args.sources) if args.sources else get_default_sync_sources(),
        days_back=args.days_back,
        max_games=args.max_games,
        season=args.season,
    )
    print(
        f"Sync complete: mode={result.mode} games={result.games_fetched} players={result.players_loaded} "
        f"stats={result.stats_loaded} signals_created={result.signals_created} "
        f"signals_updated={result.signals_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
