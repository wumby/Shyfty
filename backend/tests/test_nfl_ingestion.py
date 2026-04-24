import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.services.nfl_ingest_service import ESPNNFLClient
from app.services.nfl_normalization_service import load_nfl_boxscores_incremental


class NFLIngestionTests(unittest.TestCase):
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

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_load_nfl_boxscores_incremental_normalizes_espn_shape(self) -> None:
        teams_payload = [
            {"TeamID": "1", "Key": "KC", "FullName": "Kansas City Chiefs"},
            {"TeamID": "2", "Key": "BUF", "FullName": "Buffalo Bills"},
        ]
        boxscore_payloads = [
            {
                "GameID": "1001",
                "Season": "2025",
                "Date": "2026-01-18T21:25:00Z",
                "HomeTeamID": "1",
                "AwayTeamID": "2",
                "HomeTeam": "KC",
                "AwayTeam": "BUF",
                "HomeScore": 31,
                "AwayScore": 27,
                "PlayerGames": [
                    {
                        "PlayerID": "10",
                        "Name": "Patrick Mahomes",
                        "TeamID": "1",
                        "Position": "QB",
                        "PassingYards": 312,
                        "PassingTouchdowns": 3,
                        "PassingAttempts": 37,
                    },
                    {
                        "PlayerID": "20",
                        "Name": "James Cook",
                        "TeamID": "2",
                        "Position": "RB",
                        "RushingYards": 86,
                        "ReceivingYards": 24,
                        "RushingTouchdowns": 1,
                        "RushingAttempts": 18,
                        "Targets": 3,
                        "Receptions": 2,
                    },
                ],
            }
        ]

        result = load_nfl_boxscores_incremental(
            self.session,
            teams_payload=teams_payload,
            players_payload=[],
            boxscore_payloads=boxscore_payloads,
        )

        self.assertEqual(result.games_loaded, 1)
        self.assertEqual(result.stats_loaded, 2)
        self.assertEqual(result.players_loaded, 2)
        self.assertEqual(result.teams_loaded, 2)

        league = self.session.execute(select(League).where(League.name == "NFL")).scalar_one()
        self.assertEqual(league.name, "NFL")

        game = self.session.execute(select(Game)).scalar_one()
        self.assertEqual(game.source_system, "espn_nfl")
        self.assertEqual(game.source_id, "1001")
        self.assertEqual(str(game.season), "2025")

        chiefs = self.session.execute(select(Team).where(Team.name == "Kansas City Chiefs")).scalar_one()
        mahomes = self.session.execute(select(Player).where(Player.name == "Patrick Mahomes")).scalar_one()
        self.assertEqual(mahomes.team_id, chiefs.id)
        self.assertEqual(mahomes.source_system, "espn_nfl")

        stats = self.session.execute(
            select(PlayerGameStat).where(PlayerGameStat.player_id == mahomes.id)
        ).scalars().all()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0].passing_yards, 312)
        self.assertEqual(stats[0].touchdowns, 3)
        self.assertEqual(stats[0].source_game_id, "1001")

        team_stats = self.session.execute(
            select(TeamGameStat).order_by(TeamGameStat.team_id)
        ).scalars().all()
        self.assertEqual(len(team_stats), 2)
        self.assertEqual([stat.points for stat in team_stats], [31, 27])

    def test_espn_client_scans_back_to_find_completed_weeks(self) -> None:
        responses = {
            "https://example.test/scoreboard?season=2025&seasontype=3&week=4": {"events": []},
            "https://example.test/scoreboard?season=2025&seasontype=3&week=3": {"events": []},
            "https://example.test/scoreboard?season=2025&seasontype=3&week=2": {"events": []},
            "https://example.test/scoreboard?season=2025&seasontype=3&week=1": {"events": []},
            "https://example.test/scoreboard?season=2025&seasontype=2&week=18": {
                "events": [
                    {
                        "id": "9001",
                        "date": "2026-01-04T18:00:00Z",
                        "competitions": [
                            {
                                "status": {"type": {"completed": True}},
                                "competitors": [
                                    {"homeAway": "home", "team": {"id": "1", "abbreviation": "KC"}},
                                    {"homeAway": "away", "team": {"id": "2", "abbreviation": "BUF"}},
                                ],
                            }
                        ],
                    }
                ]
            },
            "https://example.test/summary?event=9001": {
                "header": {"season": {"year": 2025}, "week": {"number": 18}},
                "boxscore": {"players": []},
            },
        }

        def fake_fetch(url: str, timeout_seconds: float):
            return responses.get(url, {"events": []})

        client = ESPNNFLClient(base_url="https://example.test", fetch_json=fake_fetch)
        result = client.fetch_recent_completed_data(season=2025, weeks_back=1, max_games=10)

        self.assertEqual(result.game_count, 1)
        self.assertEqual(result.windows[0].season, 2025)
        self.assertEqual(result.windows[0].week, 18)
        self.assertEqual(result.boxscores[0]["GameID"], "9001")


if __name__ == "__main__":
    unittest.main()
