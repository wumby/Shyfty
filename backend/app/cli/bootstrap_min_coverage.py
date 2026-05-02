"""Bootstrap data until each NBA/NFL team has at least N games."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, or_, select

from app.db.session import SessionLocal
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.services.sync_service import run_sync


@dataclass(frozen=True)
class CoverageSummary:
    league: str
    total_teams: int
    teams_with_min_games: int
    min_games: int
    max_games: int
    min_player_stats_per_team: int
    min_team_stats_per_team: int


def _season_label_for_year(start_year: int) -> str:
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _current_nba_season() -> str:
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return _season_label_for_year(start_year)


def _previous_nba_season() -> str:
    current_start = int(_current_nba_season().split("-", 1)[0])
    return _season_label_for_year(current_start - 1)


def _team_game_counts(league_name: str) -> list[tuple[int, str, int]]:
    with SessionLocal() as db:
        rows = db.execute(
            select(
                Team.id,
                Team.name,
                func.count(func.distinct(Game.id)).label("game_count"),
            )
            .join(League, Team.league_id == League.id)
            .outerjoin(
                Game,
                and_(
                    Game.league_id == League.id,
                    or_(Game.home_team_id == Team.id, Game.away_team_id == Team.id),
                ),
            )
            .where(League.name == league_name)
            .group_by(Team.id, Team.name)
            .order_by(Team.name.asc())
        ).all()
    return [(team_id, name, int(game_count or 0)) for team_id, name, game_count in rows]


def _team_stat_minima(league_name: str) -> tuple[int, int]:
    with SessionLocal() as db:
        player_rows = db.execute(
            select(Team.id, func.count(PlayerGameStat.id))
            .join(League, Team.league_id == League.id)
            .outerjoin(Player, Player.team_id == Team.id)
            .outerjoin(PlayerGameStat, PlayerGameStat.player_id == Player.id)
            .where(League.name == league_name)
            .group_by(Team.id)
        ).all()
        team_rows = db.execute(
            select(Team.id, func.count(TeamGameStat.id))
            .join(League, Team.league_id == League.id)
            .outerjoin(TeamGameStat, TeamGameStat.team_id == Team.id)
            .where(League.name == league_name)
            .group_by(Team.id)
        ).all()

    min_player_stats = min((int(count or 0) for _, count in player_rows), default=0)
    min_team_stats = min((int(count or 0) for _, count in team_rows), default=0)
    return min_player_stats, min_team_stats


def _summarize(league_name: str, min_games_per_team: int) -> CoverageSummary:
    counts = _team_game_counts(league_name)
    values = [count for _, _, count in counts]
    player_min, team_min = _team_stat_minima(league_name)
    return CoverageSummary(
        league=league_name,
        total_teams=len(counts),
        teams_with_min_games=sum(1 for count in values if count >= min_games_per_team),
        min_games=min(values) if values else 0,
        max_games=max(values) if values else 0,
        min_player_stats_per_team=player_min,
        min_team_stats_per_team=team_min,
    )


def _print_summary(summary: CoverageSummary) -> None:
    print(
        f"{summary.league}: {summary.teams_with_min_games}/{summary.total_teams} teams >= target, "
        f"games[min={summary.min_games}, max={summary.max_games}], "
        f"player_stats_min={summary.min_player_stats_per_team}, team_stats_min={summary.min_team_stats_per_team}"
    )


def _run_until_coverage(
    *,
    source: str,
    league_name: str,
    seasons: list[str | None],
    min_games_per_team: int,
    max_games: int,
    days_back: int,
    max_passes: int,
) -> CoverageSummary:
    for pass_index in range(max_passes):
        season = seasons[pass_index % len(seasons)]
        run_sync(
            mode="bootstrap",
            sources=(source,),
            max_games=max_games,
            days_back=days_back,
            season=season,
        )
        summary = _summarize(league_name, min_games_per_team)
        _print_summary(summary)
        if summary.total_teams and summary.teams_with_min_games == summary.total_teams:
            return summary
    return _summarize(league_name, min_games_per_team)


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap NBA/NFL coverage to at least N games per team.")
    parser.add_argument("--min-games-per-team", type=int, default=5)
    parser.add_argument("--max-games", type=int, default=260)
    parser.add_argument("--days-back", type=int, default=365)
    parser.add_argument("--max-passes", type=int, default=6)
    parser.add_argument("--nba-season", default=None, help="Optional NBA season label, e.g. 2024-25")
    parser.add_argument("--nfl-season", default=None, help="Optional NFL season year, e.g. 2025")
    args = parser.parse_args()

    nba_seasons = [args.nba_season] if args.nba_season else [_current_nba_season(), _previous_nba_season()]
    nfl_seasons = [args.nfl_season] if args.nfl_season else [None]

    print("Bootstrapping NBA coverage...")
    nba_summary = _run_until_coverage(
        source="nba",
        league_name="NBA",
        seasons=nba_seasons,
        min_games_per_team=args.min_games_per_team,
        max_games=args.max_games,
        days_back=args.days_back,
        max_passes=args.max_passes,
    )

    print("Bootstrapping NFL coverage...")
    nfl_summary = _run_until_coverage(
        source="nfl",
        league_name="NFL",
        seasons=nfl_seasons,
        min_games_per_team=args.min_games_per_team,
        max_games=args.max_games,
        days_back=args.days_back,
        max_passes=max(2, args.max_passes // 2),
    )

    ok = (
        nba_summary.total_teams > 0
        and nfl_summary.total_teams > 0
        and nba_summary.teams_with_min_games == nba_summary.total_teams
        and nfl_summary.teams_with_min_games == nfl_summary.total_teams
    )

    print("Final coverage:")
    _print_summary(nba_summary)
    _print_summary(nfl_summary)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
