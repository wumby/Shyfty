import argparse

from sqlalchemy.exc import OperationalError

from app.db.session import SessionLocal
from app.services.seed_service import seed_database, seed_database_with_real_nba
from app.services.signal_generation_service import generate_signals


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed the database with real NBA data or demo fixtures.")
    parser.add_argument("--demo-only", action="store_true", help="Skip the NBA API and seed demo data for all leagues.")
    parser.add_argument("--season", default=None, help="NBA season in format 2024-25")
    parser.add_argument("--days-back", type=int, default=21)
    parser.add_argument("--max-games", type=int, default=50)
    parser.add_argument("--skip-nfl-demo", action="store_true", help="Seed only real NBA data without demo NFL rows.")
    parser.add_argument("--generate-signals", action="store_true", help="Run the signal engine after seeding.")
    args = parser.parse_args()

    try:
        with SessionLocal() as db:
            if args.demo_only:
                seed_database(db)
                message = "Seeded demo Shyfty database."
            else:
                result = seed_database_with_real_nba(
                    db,
                    season=args.season,
                    days_back=args.days_back,
                    max_games=args.max_games,
                    include_nfl_demo=not args.skip_nfl_demo,
                )
                load = result.load_result
                assert load is not None
                message = (
                    "Seeded Shyfty database with real NBA data: "
                    f"games={load.games_loaded} players={load.players_loaded} stats={load.stats_loaded}"
                )
                if result.seeded_demo_leagues:
                    message += f" demo_leagues={','.join(result.seeded_demo_leagues)}"

            if args.generate_signals:
                signal_result = generate_signals(db)
                message += (
                    f" signals_created={signal_result.created_signals}"
                    f" signals_updated={signal_result.updated_signals}"
                )
    except OperationalError as exc:
        raise SystemExit(
            "Database schema is not ready for seeding. Run `cd backend && alembic upgrade head` first. "
            f"Original error: {exc}"
        ) from exc

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
