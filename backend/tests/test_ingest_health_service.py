import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.ingest_run import IngestRun
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.shyft import Shyft
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.services.ingest_health_service import inspect_ingest_health


class IngestHealthServiceTests(unittest.TestCase):
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

    def _seed_dimensions(self):
        league = League(name="NBA")
        self.session.add(league)
        self.session.flush()
        home = Team(name="San Antonio Spurs", league_id=league.id)
        away = Team(name="Minnesota Timberwolves", league_id=league.id)
        self.session.add_all([home, away])
        self.session.flush()
        player = Player(name="Victor Wembanyama", league_id=league.id, team_id=home.id, position="C")
        self.session.add(player)
        self.session.flush()
        return league, home, away, player

    def test_reports_ok_for_fresh_final_only_data(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, 0)
        league, home, away, player = self._seed_dimensions()
        game = Game(
            league_id=league.id,
            game_date=date(2026, 5, 12),
            home_team_id=home.id,
            away_team_id=away.id,
            external_game_id="g1",
            status="final",
        )
        self.session.add(game)
        self.session.flush()
        player_stat = PlayerGameStat(player_id=player.id, game_id=game.id, points=27)
        team_stat = TeamGameStat(team_id=home.id, game_id=game.id, opponent_team_id=away.id, points=126)
        self.session.add_all([player_stat, team_stat])
        self.session.flush()
        self.session.add(
            Shyft(
                player_id=player.id,
                game_id=game.id,
                source_stat_id=player_stat.id,
                team_id=home.id,
                league_id=league.id,
                subject_type="player",
                shyft_type="OUTLIER",
                metric_name="points",
                current_value=27,
                baseline_value=18,
                z_score=2,
                explanation="fresh",
                created_at=now,
            )
        )
        self.session.add(IngestRun(started_at=now - timedelta(minutes=5), finished_at=now, status="success"))
        self.session.commit()

        report = inspect_ingest_health(self.session, now=now)

        self.assertEqual(report.status, "ok")
        self.assertEqual(report.latest_final_game_date, date(2026, 5, 12))
        self.assertEqual(report.latest_shyft_date, date(2026, 5, 12))
        self.assertEqual(report.non_final_shyfts, 0)
        self.assertEqual(report.final_games_missing_player_stats, 0)

    def test_warns_for_non_final_generated_data_and_missing_final_stats(self) -> None:
        now = datetime(2026, 5, 13, 12, 0, 0)
        league, home, away, player = self._seed_dimensions()
        final_game = Game(
            league_id=league.id,
            game_date=date(2026, 5, 12),
            home_team_id=home.id,
            away_team_id=away.id,
            external_game_id="final-missing",
            status="final",
        )
        live_game = Game(
            league_id=league.id,
            game_date=date(2026, 5, 13),
            home_team_id=home.id,
            away_team_id=away.id,
            external_game_id="live",
            status="live",
        )
        self.session.add_all([final_game, live_game])
        self.session.flush()
        live_stat = PlayerGameStat(player_id=player.id, game_id=live_game.id, points=10)
        self.session.add(live_stat)
        self.session.flush()
        self.session.add(
            Shyft(
                player_id=player.id,
                game_id=live_game.id,
                source_stat_id=live_stat.id,
                team_id=home.id,
                league_id=league.id,
                subject_type="player",
                shyft_type="OUTLIER",
                metric_name="points",
                current_value=10,
                baseline_value=20,
                z_score=-2,
                explanation="live",
                created_at=now,
            )
        )
        self.session.commit()

        report = inspect_ingest_health(self.session, now=now)

        self.assertEqual(report.status, "warning")
        self.assertEqual(report.final_games_missing_player_stats, 1)
        self.assertEqual(report.non_final_player_stats, 1)
        self.assertEqual(report.non_final_shyfts, 1)
        self.assertIn("live/scheduled games have generated stats or shyfts", report.warnings)


if __name__ == "__main__":
    unittest.main()
