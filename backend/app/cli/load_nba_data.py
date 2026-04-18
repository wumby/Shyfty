import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.nba_normalization_service import load_nba_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize a fetched NBA raw snapshot into canonical tables.")
    parser.add_argument("--snapshot-dir", type=Path, default=None)
    args = parser.parse_args()

    with SessionLocal() as db:
        result = load_nba_snapshot(db, snapshot_dir=args.snapshot_dir)

    print(
        "Loaded NBA canonical data: "
        f"snapshot={result.snapshot_dir} teams={result.teams_loaded} players={result.players_loaded} "
        f"games={result.games_loaded} stats={result.stats_loaded} skipped_stats={result.skipped_stat_rows}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
