import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.services.seed_service import seed_database, seed_database_with_real_nba


class SeedServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.engine = create_engine(
            f"sqlite:///{database_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session = self.session_factory()
        self.snapshot_dir = Path(self.temp_dir.name) / "snapshot"
        (self.snapshot_dir / "rosters").mkdir(parents=True)
        (self.snapshot_dir / "games").mkdir(parents=True)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _write_json(self, relative_path: str, payload: dict) -> None:
        target = self.snapshot_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload), encoding="utf-8")

    def _write_snapshot(self) -> None:
        self._write_json(
            "manifest.json",
            {
                "source_system": "nba_stats",
                "season": "2024-25",
                "season_type": "Regular Season",
                "game_ids": ["0022400001"],
                "team_ids": [1610612744, 1610612747],
            },
        )
        self._write_json(
            "leaguegamelog.json",
            {
                "resultSets": [
                    {
                        "name": "LeagueGameLog",
                        "headers": ["SEASON_ID", "TEAM_ID", "TEAM_ABBREVIATION", "TEAM_NAME", "GAME_ID", "GAME_DATE", "MATCHUP"],
                        "rowSet": [
                            ["22024", 1610612744, "GSW", "Golden State Warriors", "0022400001", "2025-01-05", "GSW vs. LAL"],
                            ["22024", 1610612747, "LAL", "Los Angeles Lakers", "0022400001", "2025-01-05", "LAL @ GSW"],
                        ],
                    }
                ]
            },
        )
        self._write_json(
            "commonallplayers.json",
            {
                "resultSets": [
                    {
                        "name": "CommonAllPlayers",
                        "headers": ["PERSON_ID", "DISPLAY_FIRST_LAST", "TEAM_ID"],
                        "rowSet": [
                            [201939, "Stephen Curry", 1610612744],
                            [2544, "LeBron James", 1610612747],
                        ],
                    }
                ]
            },
        )
        self._write_json(
            "rosters/1610612744.json",
            {
                "resultSets": [
                    {
                        "name": "CommonTeamRoster",
                        "headers": ["TeamID", "SEASON", "LeagueID", "PLAYER", "PLAYER_SLUG", "NUM", "POSITION", "HEIGHT", "WEIGHT", "BIRTH_DATE", "AGE", "EXP", "SCHOOL", "PLAYER_ID"],
                        "rowSet": [[1610612744, "2024-25", "00", "Stephen Curry", "stephen-curry", "30", "G", "6-2", "185", "", 0, "", "", 201939]],
                    }
                ]
            },
        )
        self._write_json(
            "rosters/1610612747.json",
            {
                "resultSets": [
                    {
                        "name": "CommonTeamRoster",
                        "headers": ["TeamID", "SEASON", "LeagueID", "PLAYER", "PLAYER_SLUG", "NUM", "POSITION", "HEIGHT", "WEIGHT", "BIRTH_DATE", "AGE", "EXP", "SCHOOL", "PLAYER_ID"],
                        "rowSet": [[1610612747, "2024-25", "00", "LeBron James", "lebron-james", "23", "F", "6-9", "250", "", 0, "", "", 2544]],
                    }
                ]
            },
        )
        self._write_json(
            "games/0022400001_traditional.json",
            {
                "resultSets": [
                    {
                        "name": "PlayerStats",
                        "headers": [
                            "GAME_ID",
                            "TEAM_ID",
                            "PLAYER_ID",
                            "PLAYER_NAME",
                            "START_POSITION",
                            "MIN",
                            "REB",
                            "AST",
                            "PTS",
                            "STL",
                            "BLK",
                            "TO",
                            "PLUS_MINUS",
                            "FG_PCT",
                            "FG3_PCT",
                            "FT_PCT",
                        ],
                        "rowSet": [
                            ["0022400001", 1610612744, 201939, "Stephen Curry", "G", "34:00", 5, 7, 32, 1, 0, 3, 8, 0.52, 0.45, 1.0],
                            ["0022400001", 1610612747, 2544, "LeBron James", "F", "36:00", 8, 9, 28, 2, 1, 4, -8, 0.49, 0.33, 0.75],
                        ],
                    }
                ]
            },
        )
        self._write_json(
            "games/0022400001_usage.json",
            {
                "resultSets": [
                    {
                        "name": "sqlPlayersUsage",
                        "headers": ["GAME_ID", "TEAM_ID", "PLAYER_ID", "USG_PCT"],
                        "rowSet": [
                            ["0022400001", 1610612744, 201939, 31.2],
                            ["0022400001", 1610612747, 2544, 29.8],
                        ],
                    }
                ]
            },
        )

    def test_real_nba_seed_loads_snapshot_and_keeps_demo_nfl(self) -> None:
        seed_database(self.session)
        self._write_snapshot()

        result = seed_database_with_real_nba(
            self.session,
            include_nfl_demo=True,
            snapshot_dir=self.snapshot_dir,
        )

        self.assertEqual(result.mode, "real_nba")
        self.assertIsNone(result.fetch_result)
        self.assertIsNotNone(result.load_result)
        assert result.load_result is not None
        self.assertEqual(result.load_result.games_loaded, 1)
        self.assertEqual(result.seeded_demo_leagues, ("NFL",))

        league_names = self.session.execute(select(League.name).order_by(League.name)).scalars().all()
        self.assertEqual(league_names, ["NBA", "NFL"])

        nba_players = self.session.execute(
            select(Player.name)
            .join(League, Player.league_id == League.id)
            .where(League.name == "NBA")
            .order_by(Player.name)
        ).scalars().all()
        self.assertEqual(nba_players, ["LeBron James", "Stephen Curry"])
        self.assertNotIn("Luka Doncic", nba_players)

        nfl_players = self.session.execute(
            select(Player.name)
            .join(League, Player.league_id == League.id)
            .where(League.name == "NFL")
            .order_by(Player.name)
        ).scalars().all()
        self.assertEqual(nfl_players, ["Josh Allen", "Justin Jefferson", "Patrick Mahomes"])

        nba_stat_count = self.session.execute(
            select(func.count())
            .select_from(PlayerGameStat)
            .join(Player, PlayerGameStat.player_id == Player.id)
            .join(League, Player.league_id == League.id)
            .where(League.name == "NBA")
        ).scalar_one()
        nfl_stat_count = self.session.execute(
            select(func.count())
            .select_from(PlayerGameStat)
            .join(Player, PlayerGameStat.player_id == Player.id)
            .join(League, Player.league_id == League.id)
            .where(League.name == "NFL")
        ).scalar_one()
        self.assertEqual(nba_stat_count, 2)
        self.assertEqual(nfl_stat_count, 15)


if __name__ == "__main__":
    unittest.main()
