import argparse

from app.db.session import SessionLocal
from app.services.reset_service import reset_legacy_seeded_nfl, reset_sports_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset old seeded or ingested sports data from the Shyfty database.")
    parser.add_argument(
        "--mode",
        choices=["legacy-seeded-nfl", "sports-data"],
        required=True,
        help="legacy-seeded-nfl removes the old fake NFL rows; sports-data wipes all sports entities and sync state but keeps user/auth tables.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted without modifying the database.")
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.mode == "legacy-seeded-nfl":
            result = reset_legacy_seeded_nfl(db, dry_run=args.dry_run)
        else:
            result = reset_sports_data(db, dry_run=args.dry_run)

    print(
        f"{'Dry run' if args.dry_run else 'Reset complete'}: mode={result.mode} leagues={result.leagues_deleted} teams={result.teams_deleted} "
        f"players={result.players_deleted} games={result.games_deleted} signals={result.signals_deleted} "
        f"player_stats={result.player_stats_deleted} team_stats={result.team_stats_deleted}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
