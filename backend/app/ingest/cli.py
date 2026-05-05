from __future__ import annotations

import argparse
from datetime import date

from app.core.config import settings
from app.services.schedule_sync_service import discover_schedule, hydrate_games, sync_league


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    return date.fromisoformat(raw)


def _resolve_leagues(args) -> list[str]:
    if args.all:
        leagues: list[str] = []
        if settings.enable_nba_sync:
            leagues.append("nba")
        if settings.enable_nfl_sync:
            leagues.append("nfl")
        return leagues
    return [args.league.lower()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Schedule-first ingest CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("discover", "hydrate", "sync"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--league", default="NBA", choices=["NBA", "NFL"])
        cmd.add_argument("--all", action="store_true")
        cmd.add_argument("--from", dest="date_from", default=None)
        cmd.add_argument("--to", dest="date_to", default=None)
        cmd.add_argument("--force", action="store_true")

    args = parser.parse_args()
    leagues = _resolve_leagues(args)
    start = _parse_date(args.date_from)
    end = _parse_date(args.date_to)

    for league in leagues:
        if args.command == "discover":
            result = discover_schedule(league=league, start_date=start, end_date=end)
        elif args.command == "hydrate":
            result = hydrate_games(league=league, start_date=start, end_date=end, force=args.force)
        else:
            result = sync_league(league=league, start_date=start, end_date=end, force=args.force)
        print(
            f"[{league}] discovered={result.discovered_games} skipped={result.skipped_games} hydrated={result.hydrated_games} "
            f"players={result.players_loaded} team_stats={result.team_stats_loaded} player_stats={result.player_stats_loaded} "
            f"shyfts_created={result.shyfts_created} shyfts_updated={result.shyfts_updated}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
