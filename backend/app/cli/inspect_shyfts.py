import argparse
import json

from app.db.session import SessionLocal
from app.services.player_service import get_player_shyfts
from app.services.shyft_inspection_service import inspect_shyft
from app.services.shyft_service import list_shyfts


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Shyfty shyfts and their source context.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recent_parser = subparsers.add_parser("recent", help="List recent generated shyfts.")
    recent_parser.add_argument("--limit", type=int, default=10)

    player_parser = subparsers.add_parser("player", help="List recent shyfts for one player.")
    player_parser.add_argument("player_id", type=int)

    signal_parser = subparsers.add_parser("shyft", help="Inspect a single shyft with source stats and baseline samples.")
    signal_parser.add_argument("shyft_id", type=int)

    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "recent":
            shyfts = list_shyfts(db=db, league=None, team=None, player=None, shyft_type=None, limit=args.limit)
            items = shyfts.items if hasattr(shyfts, "items") else shyfts
            _print_json([shyft.model_dump(mode="json") for shyft in items])
            return 0

        if args.command == "player":
            shyfts = get_player_shyfts(db, args.player_id)
            _print_json([shyft.model_dump(mode="json") for shyft in shyfts[:10]])
            return 0

        trace = inspect_shyft(db, args.shyft_id)
        if trace is None:
            print(f"Shyft {args.shyft_id} not found.")
            return 1
        _print_json(trace.model_dump(mode="json"))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
