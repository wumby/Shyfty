"""Unified ingest CLI: fetch NBA data → normalize → generate signals."""
import argparse

from app.services.ingest_pipeline import run_full_ingest


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the full NBA ingest pipeline.")
    parser.add_argument("--days-back", type=int, default=21)
    parser.add_argument("--max-games", type=int, default=30)
    parser.add_argument("--season", default=None, help="e.g. 2024-25")
    args = parser.parse_args()

    result = run_full_ingest(
        days_back=args.days_back,
        max_games=args.max_games,
        season=args.season,
    )
    print(
        f"Ingest complete: games={result.games_fetched} players={result.players_loaded} "
        f"stats={result.stats_loaded} signals_created={result.signals_created} "
        f"signals_updated={result.signals_updated}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
