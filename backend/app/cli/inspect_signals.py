import argparse
import json

from app.db.session import SessionLocal
from app.services.player_service import get_player_signals
from app.services.signal_inspection_service import inspect_signal
from app.services.signal_service import list_signals


def _print_json(value) -> None:
    print(json.dumps(value, indent=2, default=str))


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Shyfty signals and their source context.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    recent_parser = subparsers.add_parser("recent", help="List recent generated signals.")
    recent_parser.add_argument("--limit", type=int, default=10)

    player_parser = subparsers.add_parser("player", help="List recent signals for one player.")
    player_parser.add_argument("player_id", type=int)

    signal_parser = subparsers.add_parser("signal", help="Inspect a single signal with source stats and baseline samples.")
    signal_parser.add_argument("signal_id", type=int)

    args = parser.parse_args()

    with SessionLocal() as db:
        if args.command == "recent":
            signals = list_signals(db=db, league=None, team=None, player=None, signal_type=None, limit=args.limit)
            items = signals.items if hasattr(signals, "items") else signals
            _print_json([signal.model_dump(mode="json") for signal in items])
            return 0

        if args.command == "player":
            signals = get_player_signals(db, args.player_id)
            _print_json([signal.model_dump(mode="json") for signal in signals[:10]])
            return 0

        trace = inspect_signal(db, args.signal_id)
        if trace is None:
            print(f"Signal {args.signal_id} not found.")
            return 1
        _print_json(trace.model_dump(mode="json"))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
