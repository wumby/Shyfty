import argparse

from app.services.nba_ingest_service import fetch_recent_nba_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch recent NBA data into local raw payload files.")
    parser.add_argument("--season", default=None, help="Season in NBA format, e.g. 2024-25")
    parser.add_argument("--days-back", type=int, default=21)
    parser.add_argument("--max-games", type=int, default=50)
    args = parser.parse_args()

    result = fetch_recent_nba_data(
        season=args.season,
        days_back=args.days_back,
        max_games=args.max_games,
    )
    print(
        "Fetched NBA raw snapshot: "
        f"dir={result.output_dir} games={result.game_count} teams={result.team_count} "
        f"rosters={result.roster_count} skipped_games={result.skipped_games}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
