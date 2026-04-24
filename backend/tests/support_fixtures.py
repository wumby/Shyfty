from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team


def load_sample_signal_dataset(db: Session) -> None:
    dates = [date.today() - timedelta(days=offset) for offset in [14, 11, 8, 5, 2]]
    league = League(name="NBA")
    db.add(league)
    db.flush()

    team_names = ["Dallas Mavericks", "Denver Nuggets", "Golden State Warriors"]
    teams: dict[str, Team] = {}
    for team_name in team_names:
        team = Team(name=team_name, league_id=league.id)
        db.add(team)
        db.flush()
        teams[team_name] = team

    games: list[Game] = []
    matchups = [
        ("Dallas Mavericks", "Denver Nuggets"),
        ("Golden State Warriors", "Dallas Mavericks"),
        ("Denver Nuggets", "Golden State Warriors"),
        ("Dallas Mavericks", "Golden State Warriors"),
        ("Denver Nuggets", "Dallas Mavericks"),
    ]
    for index, (home_name, away_name) in enumerate(matchups):
        game = Game(
            league_id=league.id,
            game_date=dates[index],
            home_team_id=teams[home_name].id,
            away_team_id=teams[away_name].id,
        )
        db.add(game)
        db.flush()
        games.append(game)

    player_payloads = [
        (
            "Luka Doncic",
            "Dallas Mavericks",
            "G",
            [
                {"points": 29, "rebounds": 8, "assists": 9, "usage_rate": 34.1},
                {"points": 31, "rebounds": 9, "assists": 10, "usage_rate": 35.4},
                {"points": 28, "rebounds": 10, "assists": 8, "usage_rate": 33.6},
                {"points": 33, "rebounds": 11, "assists": 12, "usage_rate": 36.2},
                {"points": 44, "rebounds": 12, "assists": 13, "usage_rate": 39.7},
            ],
        ),
        (
            "Nikola Jokic",
            "Denver Nuggets",
            "C",
            [
                {"points": 25, "rebounds": 13, "assists": 11, "usage_rate": 29.2},
                {"points": 27, "rebounds": 12, "assists": 10, "usage_rate": 30.1},
                {"points": 26, "rebounds": 14, "assists": 12, "usage_rate": 29.7},
                {"points": 28, "rebounds": 13, "assists": 11, "usage_rate": 30.0},
                {"points": 27, "rebounds": 13, "assists": 11, "usage_rate": 29.9},
            ],
        ),
        (
            "Stephen Curry",
            "Golden State Warriors",
            "G",
            [
                {"points": 30, "rebounds": 4, "assists": 6, "usage_rate": 31.0},
                {"points": 32, "rebounds": 5, "assists": 5, "usage_rate": 31.4},
                {"points": 29, "rebounds": 4, "assists": 7, "usage_rate": 30.6},
                {"points": 27, "rebounds": 5, "assists": 6, "usage_rate": 30.2},
                {"points": 18, "rebounds": 3, "assists": 4, "usage_rate": 24.8},
            ],
        ),
    ]

    for player_name, team_name, position, stat_rows in player_payloads:
        player = Player(name=player_name, league_id=league.id, team_id=teams[team_name].id, position=position)
        db.add(player)
        db.flush()
        for index, stat_payload in enumerate(stat_rows):
            db.add(PlayerGameStat(player_id=player.id, game_id=games[index].id, **stat_payload))

    db.commit()
