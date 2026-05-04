import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.league import League
from app.models.team import Team
from app.services import schedule_sync_service as svc


class _FakeProvider:
    league = "nba"

    def discover_schedule(self, *, start_date: date, end_date: date):
        del start_date, end_date
        return [
            svc.ProviderGame(
                league="nba",
                external_game_id="g1",
                game_date=date.today(),
                status="scheduled",
                home_team_external_id="h1",
                away_team_external_id="a1",
                raw_payload={"id": "g1"},
            )
        ]

    def fetch_game_detail(self, external_game_id: str):
        raise NotImplementedError


class ScheduleSyncServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.engine = create_engine(f"sqlite:///{database_path}", future=True, connect_args={"check_same_thread": False})
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(bind=self.engine)

    def tearDown(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_discovery_upserts_games_idempotently(self) -> None:
        with patch("app.services.schedule_sync_service.SessionLocal", self.session_factory):
            with patch("app.services.schedule_sync_service._get_provider", return_value=_FakeProvider()):
                svc.discover_schedule(league="nba")
                svc.discover_schedule(league="nba")

        with self.session_factory() as db:
            league = db.execute(select(League).where(League.name == "NBA")).scalar_one()
            games = db.execute(select(Game).where(Game.league_id == league.id)).scalars().all()
            teams = db.execute(select(Team).where(Team.league_id == league.id)).scalars().all()
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0].external_game_id, "g1")
            self.assertEqual(len(teams), 2)

    def test_hydration_selector_skips_old_final_games(self) -> None:
        game = Game(
            league_id=1,
            game_date=date.today() - timedelta(days=10),
            season="2025-26",
            home_team_id=1,
            away_team_id=2,
            external_game_id="x",
            status="final",
            last_hydrated_at=datetime.utcnow() - timedelta(days=5),
        )
        self.assertFalse(svc.needs_hydration(game, now=datetime.utcnow(), force=False))

    def test_hydration_selector_rechecks_recent_final_games(self) -> None:
        game = Game(
            league_id=1,
            game_date=date.today() - timedelta(days=1),
            season="2025-26",
            home_team_id=1,
            away_team_id=2,
            external_game_id="x",
            status="final",
            last_hydrated_at=datetime.utcnow() - timedelta(hours=10),
        )
        self.assertTrue(svc.needs_hydration(game, now=datetime.utcnow(), force=False))

    def test_hydration_selector_hydrates_non_final_games(self) -> None:
        game = Game(
            league_id=1,
            game_date=date.today(),
            season="2025-26",
            home_team_id=1,
            away_team_id=2,
            external_game_id="x",
            status="scheduled",
            last_hydrated_at=datetime.utcnow() - timedelta(days=20),
        )
        self.assertTrue(svc.needs_hydration(game, now=datetime.utcnow(), force=False))


if __name__ == "__main__":
    unittest.main()
