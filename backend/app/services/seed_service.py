from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.raw_ingest_event import RawIngestEvent
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.signal_comment import SignalComment
from app.models.signal_reaction import SignalReaction
from app.models.team import Team
from app.models.user_favorite import UserFavorite
from app.services.nba_ingest_service import FetchResult, fetch_recent_nba_data
from app.services.nba_normalization_service import LoadResult, load_nba_snapshot


@dataclass(frozen=True)
class SeedResult:
    mode: str
    fetch_result: Optional[FetchResult] = None
    load_result: Optional[LoadResult] = None
    seeded_demo_leagues: tuple[str, ...] = ()


def build_seed_payload(*, leagues: Optional[tuple[str, ...]] = None) -> dict:
    today = date.today()
    selected_leagues = set(leagues or ("NBA", "NFL"))

    payload = {"dates": [today - timedelta(days=offset) for offset in [14, 11, 8, 5, 2]]}

    if "NBA" in selected_leagues:
        payload["NBA"] = {
            "teams": ["Dallas Mavericks", "Denver Nuggets", "Golden State Warriors"],
            "players": [
                {
                    "name": "Luka Doncic",
                    "team": "Dallas Mavericks",
                    "position": "G",
                    "stats": [
                        {"points": 29, "rebounds": 8, "assists": 9, "usage_rate": 34.1},
                        {"points": 31, "rebounds": 9, "assists": 10, "usage_rate": 35.4},
                        {"points": 28, "rebounds": 10, "assists": 8, "usage_rate": 33.6},
                        {"points": 33, "rebounds": 11, "assists": 12, "usage_rate": 36.2},
                        {"points": 44, "rebounds": 12, "assists": 13, "usage_rate": 39.7},
                    ],
                },
                {
                    "name": "Nikola Jokic",
                    "team": "Denver Nuggets",
                    "position": "C",
                    "stats": [
                        {"points": 25, "rebounds": 13, "assists": 11, "usage_rate": 29.2},
                        {"points": 27, "rebounds": 12, "assists": 10, "usage_rate": 30.1},
                        {"points": 26, "rebounds": 14, "assists": 12, "usage_rate": 29.7},
                        {"points": 28, "rebounds": 13, "assists": 11, "usage_rate": 30.0},
                        {"points": 27, "rebounds": 13, "assists": 11, "usage_rate": 29.9},
                    ],
                },
                {
                    "name": "Stephen Curry",
                    "team": "Golden State Warriors",
                    "position": "G",
                    "stats": [
                        {"points": 30, "rebounds": 4, "assists": 6, "usage_rate": 31.0},
                        {"points": 32, "rebounds": 5, "assists": 5, "usage_rate": 31.4},
                        {"points": 29, "rebounds": 4, "assists": 7, "usage_rate": 30.6},
                        {"points": 27, "rebounds": 5, "assists": 6, "usage_rate": 30.2},
                        {"points": 18, "rebounds": 3, "assists": 4, "usage_rate": 24.8},
                    ],
                },
            ],
            "games": [
                ("Dallas Mavericks", "Denver Nuggets"),
                ("Golden State Warriors", "Dallas Mavericks"),
                ("Denver Nuggets", "Golden State Warriors"),
                ("Dallas Mavericks", "Golden State Warriors"),
                ("Denver Nuggets", "Dallas Mavericks"),
            ],
        }

    if "NFL" in selected_leagues:
        payload["NFL"] = {
            "teams": ["Kansas City Chiefs", "Buffalo Bills", "Minnesota Vikings"],
            "players": [
                {
                    "name": "Patrick Mahomes",
                    "team": "Kansas City Chiefs",
                    "position": "QB",
                    "stats": [
                        {"passing_yards": 286, "rushing_yards": 21, "touchdowns": 2, "usage_rate": 0.72},
                        {"passing_yards": 301, "rushing_yards": 18, "touchdowns": 3, "usage_rate": 0.74},
                        {"passing_yards": 278, "rushing_yards": 25, "touchdowns": 2, "usage_rate": 0.73},
                        {"passing_yards": 295, "rushing_yards": 17, "touchdowns": 3, "usage_rate": 0.71},
                        {"passing_yards": 372, "rushing_yards": 34, "touchdowns": 4, "usage_rate": 0.79},
                    ],
                },
                {
                    "name": "Josh Allen",
                    "team": "Buffalo Bills",
                    "position": "QB",
                    "stats": [
                        {"passing_yards": 264, "rushing_yards": 41, "touchdowns": 3, "usage_rate": 0.76},
                        {"passing_yards": 271, "rushing_yards": 38, "touchdowns": 2, "usage_rate": 0.77},
                        {"passing_yards": 269, "rushing_yards": 42, "touchdowns": 3, "usage_rate": 0.76},
                        {"passing_yards": 267, "rushing_yards": 39, "touchdowns": 2, "usage_rate": 0.75},
                        {"passing_yards": 265, "rushing_yards": 40, "touchdowns": 3, "usage_rate": 0.76},
                    ],
                },
                {
                    "name": "Justin Jefferson",
                    "team": "Minnesota Vikings",
                    "position": "WR",
                    "stats": [
                        {"receiving_yards": 118, "touchdowns": 1, "usage_rate": 0.29},
                        {"receiving_yards": 124, "touchdowns": 1, "usage_rate": 0.31},
                        {"receiving_yards": 121, "touchdowns": 1, "usage_rate": 0.30},
                        {"receiving_yards": 115, "touchdowns": 1, "usage_rate": 0.28},
                        {"receiving_yards": 63, "touchdowns": 0, "usage_rate": 0.18},
                    ],
                },
            ],
            "games": [
                ("Kansas City Chiefs", "Buffalo Bills"),
                ("Minnesota Vikings", "Kansas City Chiefs"),
                ("Buffalo Bills", "Minnesota Vikings"),
                ("Kansas City Chiefs", "Minnesota Vikings"),
                ("Buffalo Bills", "Kansas City Chiefs"),
            ],
        }

    return payload


def _clear_seedable_data(db: Session) -> None:
    existing_tables = set(inspect(db.get_bind()).get_table_names())
    for model in (
        UserFavorite,
        SignalReaction,
        SignalComment,
        RollingMetricBaselineSample,
        RawIngestEvent,
        RollingMetric,
        PlayerGameStat,
        Signal,
        Game,
        Player,
        Team,
        League,
    ):
        if model.__tablename__ in existing_tables:
            db.query(model).delete()


def _seed_payload(db: Session, payload: dict) -> tuple[str, ...]:
    leagues: dict[str, League] = {}
    teams: dict[tuple[str, str], Team] = {}
    seeded_leagues: list[str] = []

    for league_name, league_payload in payload.items():
        if league_name == "dates":
            continue

        league = League(name=league_name)
        db.add(league)
        db.flush()
        leagues[league_name] = league
        seeded_leagues.append(league_name)

        for team_name in league_payload["teams"]:
            team = Team(name=team_name, league_id=league.id)
            db.add(team)
            db.flush()
            teams[(league_name, team_name)] = team

        games = []
        for index, matchup in enumerate(league_payload["games"]):
            home_name, away_name = matchup
            game = Game(
                league_id=league.id,
                game_date=payload["dates"][index],
                home_team_id=teams[(league_name, home_name)].id,
                away_team_id=teams[(league_name, away_name)].id,
            )
            db.add(game)
            db.flush()
            games.append(game)

        for player_payload in league_payload["players"]:
            player = Player(
                name=player_payload["name"],
                league_id=league.id,
                team_id=teams[(league_name, player_payload["team"])].id,
                position=player_payload["position"],
            )
            db.add(player)
            db.flush()

            for index, stat_payload in enumerate(player_payload["stats"]):
                db.add(PlayerGameStat(player_id=player.id, game_id=games[index].id, **stat_payload))

    return tuple(seeded_leagues)


def seed_database(db: Session) -> None:
    payload = build_seed_payload()
    _clear_seedable_data(db)
    _seed_payload(db, payload)
    db.commit()


def seed_database_with_real_nba(
    db: Session,
    *,
    season: Optional[str] = None,
    days_back: int = 21,
    max_games: int = 50,
    include_nfl_demo: bool = True,
    snapshot_dir: Optional[Path] = None,
) -> SeedResult:
    if snapshot_dir is None:
        fetch_result = fetch_recent_nba_data(
            season=season,
            days_back=days_back,
            max_games=max_games,
        )
        resolved_snapshot_dir = fetch_result.output_dir
    else:
        fetch_result = None
        resolved_snapshot_dir = snapshot_dir

    _clear_seedable_data(db)

    load_result = load_nba_snapshot(db, snapshot_dir=resolved_snapshot_dir, clear_since=None)
    seeded_demo_leagues: tuple[str, ...] = ()
    if include_nfl_demo:
        seeded_demo_leagues = _seed_payload(db, build_seed_payload(leagues=("NFL",)))

    db.commit()

    return SeedResult(
        mode="real_nba",
        fetch_result=fetch_result,
        load_result=load_result,
        seeded_demo_leagues=seeded_demo_leagues,
    )
