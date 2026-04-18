import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team
from app.services.nba_normalization_service import load_nba_snapshot


class NBAIngestionTests(unittest.TestCase):
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

    def test_load_nba_snapshot_normalizes_raw_payloads(self) -> None:
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
                        "headers": ["GAME_ID", "TEAM_ID", "PLAYER_ID", "PLAYER_NAME", "START_POSITION", "MIN", "REB", "AST", "PTS"],
                        "rowSet": [
                            ["0022400001", 1610612744, 201939, "Stephen Curry", "G", "34:00", 5, 7, 32],
                            ["0022400001", 1610612747, 2544, "LeBron James", "F", "36:00", 8, 9, 28],
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

        result = load_nba_snapshot(self.session, snapshot_dir=self.snapshot_dir)

        self.assertEqual(result.games_loaded, 1)
        self.assertEqual(result.players_loaded, 2)
        self.assertEqual(result.teams_loaded, 2)
        self.assertEqual(result.stats_loaded, 2)
        self.assertEqual(result.skipped_stat_rows, 0)

        game = self.session.execute(select(Game)).scalar_one()
        self.assertEqual(game.source_system, "nba_stats")
        self.assertEqual(game.source_id, "0022400001")

        player_count = self.session.execute(select(func.count()).select_from(Player)).scalar_one()
        team_count = self.session.execute(select(func.count()).select_from(Team)).scalar_one()
        stat_count = self.session.execute(select(func.count()).select_from(PlayerGameStat)).scalar_one()
        self.assertEqual(player_count, 2)
        self.assertEqual(team_count, 2)
        self.assertEqual(stat_count, 2)

        curry = self.session.execute(select(Player).where(Player.name == "Stephen Curry")).scalar_one()
        self.assertEqual(curry.position, "G")
        self.assertEqual(curry.source_id, "201939")
        curry_stat = self.session.execute(select(PlayerGameStat).where(PlayerGameStat.player_id == curry.id)).scalar_one()
        self.assertEqual(curry_stat.source_system, "nba_stats")
        self.assertEqual(curry_stat.source_game_id, "0022400001")
        self.assertEqual(curry_stat.source_player_id, "201939")
        self.assertEqual(curry_stat.raw_record_index, 0)
        self.assertTrue(curry_stat.raw_snapshot_path)
        self.assertTrue(curry_stat.raw_payload_path.endswith("0022400001_traditional.json"))


if __name__ == "__main__":
    unittest.main()
