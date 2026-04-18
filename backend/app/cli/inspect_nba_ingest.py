import argparse
import json

from app.db.session import SessionLocal
from app.services.nba_ingest_inspection_service import (
    get_ingest_summary,
    list_recent_nba_games,
    list_recent_nba_players,
)


def _dump(value) -> None:
    print(json.dumps(value, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect normalized NBA ingest results.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    summary_parser = subparsers.add_parser("summary")
    summary_parser.add_argument("--limit", type=int, default=10)

    games_parser = subparsers.add_parser("games")
    games_parser.add_argument("--limit", type=int, default=10)

    players_parser = subparsers.add_parser("players")
    players_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "summary":
            _dump(get_ingest_summary(db))
            return 0
        if args.command == "games":
            _dump(list_recent_nba_games(db, limit=args.limit))
            return 0
        _dump(list_recent_nba_players(db, limit=args.limit))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
