import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.comment_report import CommentReport
from app.models.game import Game
from app.models.ingest_run import IngestRun
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.raw_ingest_event import RawIngestEvent
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.shyft import Shyft
from app.models.shyft_comment import ShyftComment
from app.models.shyft_reaction import ShyftReactionRecord
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user import User
from app.services.retention_service import cleanup_non_final_generated_data, prune_retained_data


class RetentionServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.engine = create_engine(
            f"sqlite:///{database_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(self.engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session = self.session_factory()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _count(self, model) -> int:
        return int(self.session.execute(select(func.count()).select_from(model)).scalar_one())

    def _seed_dataset(self) -> dict[str, int]:
        now = datetime(2026, 5, 7, 12, 0, 0)
        league = League(name="NBA")
        self.session.add(league)
        self.session.flush()

        home = Team(name="Denver Nuggets", league_id=league.id)
        away = Team(name="Dallas Mavericks", league_id=league.id)
        self.session.add_all([home, away])
        self.session.flush()

        player = Player(name="Nikola Jokic", league_id=league.id, team_id=home.id, position="C")
        user = User(email="user@example.com", password_hash="hash")
        self.session.add_all([player, user])
        self.session.flush()

        old_game = Game(
            league_id=league.id,
            game_date=date(2026, 2, 1),
            home_team_id=home.id,
            away_team_id=away.id,
            external_game_id="old-game",
        )
        recent_game = Game(
            league_id=league.id,
            game_date=date(2026, 5, 1),
            home_team_id=home.id,
            away_team_id=away.id,
            external_game_id="recent-game",
        )
        self.session.add_all([old_game, recent_game])
        self.session.flush()

        old_player_stat = PlayerGameStat(player_id=player.id, game_id=old_game.id, points=40)
        recent_player_stat = PlayerGameStat(player_id=player.id, game_id=recent_game.id, points=28)
        old_team_stat = TeamGameStat(team_id=home.id, game_id=old_game.id, opponent_team_id=away.id, points=120)
        recent_team_stat = TeamGameStat(team_id=home.id, game_id=recent_game.id, opponent_team_id=away.id, points=115)
        self.session.add_all([old_player_stat, recent_player_stat, old_team_stat, recent_team_stat])
        self.session.flush()

        old_metric = RollingMetric(
            player_id=player.id,
            game_id=old_game.id,
            source_stat_id=old_player_stat.id,
            metric_name="points",
            rolling_avg=24.0,
            rolling_stddev=4.0,
            z_score=4.0,
            updated_at=now - timedelta(days=90),
        )
        recent_metric = RollingMetric(
            player_id=player.id,
            game_id=recent_game.id,
            source_stat_id=recent_player_stat.id,
            metric_name="points",
            rolling_avg=25.0,
            rolling_stddev=3.0,
            z_score=1.0,
            updated_at=now - timedelta(days=1),
        )
        self.session.add_all([old_metric, recent_metric])
        self.session.flush()

        old_sample = RollingMetricBaselineSample(
            rolling_metric_id=old_metric.id,
            player_game_stat_id=old_player_stat.id,
            sample_order=1,
        )
        recent_sample = RollingMetricBaselineSample(
            rolling_metric_id=recent_metric.id,
            player_game_stat_id=recent_player_stat.id,
            sample_order=1,
        )
        self.session.add_all([old_sample, recent_sample])
        self.session.flush()

        old_shyft = Shyft(
            player_id=player.id,
            game_id=old_game.id,
            rolling_metric_id=old_metric.id,
            source_stat_id=old_player_stat.id,
            team_id=home.id,
            league_id=league.id,
            subject_type="player",
            shyft_type="OUTLIER",
            metric_name="points",
            current_value=40,
            baseline_value=24,
            z_score=4.0,
            explanation="old",
            created_at=now - timedelta(days=90),
        )
        recent_shyft = Shyft(
            player_id=player.id,
            game_id=recent_game.id,
            rolling_metric_id=recent_metric.id,
            source_stat_id=recent_player_stat.id,
            team_id=home.id,
            league_id=league.id,
            subject_type="player",
            shyft_type="OUTLIER",
            metric_name="assists",
            current_value=12,
            baseline_value=8,
            z_score=2.0,
            explanation="recent",
            created_at=now - timedelta(days=1),
        )
        self.session.add_all([old_shyft, recent_shyft])
        self.session.flush()

        comment = ShyftComment(shyft_id=old_shyft.id, user_id=user.id, body="old comment")
        reaction = ShyftReactionRecord(shyft_id=old_shyft.id, user_id=user.id, type="like")
        self.session.add_all([comment, reaction])
        self.session.flush()
        report = CommentReport(comment_id=comment.id, reporter_user_id=user.id, reason="spam")
        self.session.add(report)

        old_raw = RawIngestEvent(
            source="nba",
            source_type="api",
            external_id="old-raw",
            ingested_at=now - timedelta(days=30),
        )
        recent_raw = RawIngestEvent(
            source="nba",
            source_type="api",
            external_id="recent-raw",
            ingested_at=now - timedelta(days=3),
        )
        old_run = IngestRun(started_at=now - timedelta(days=120), status="success")
        recent_run = IngestRun(started_at=now - timedelta(days=3), status="success")
        self.session.add_all([old_raw, recent_raw, old_run, recent_run])
        self.session.commit()

        return {
            "now": now,
            "old_game_id": old_game.id,
            "recent_game_id": recent_game.id,
            "player_id": player.id,
            "user_id": user.id,
        }

    def test_dry_run_counts_without_deleting(self) -> None:
        ids = self._seed_dataset()

        result = prune_retained_data(
            self.session,
            sports_days=60,
            raw_ingest_days=14,
            ingest_run_days=90,
            dry_run=True,
            now=ids["now"],
        )

        self.assertTrue(result.dry_run)
        self.assertEqual(result.games_deleted, 1)
        self.assertEqual(result.player_stats_deleted, 1)
        self.assertEqual(result.team_stats_deleted, 1)
        self.assertEqual(result.rolling_metrics_deleted, 1)
        self.assertEqual(result.baseline_samples_deleted, 1)
        self.assertEqual(result.shyfts_deleted, 1)
        self.assertEqual(result.comments_deleted, 1)
        self.assertEqual(result.reactions_deleted, 1)
        self.assertEqual(result.reports_deleted, 1)
        self.assertEqual(result.raw_events_deleted, 1)
        self.assertEqual(result.ingest_runs_deleted, 1)
        self.assertEqual(self._count(Game), 2)
        self.assertEqual(self._count(Shyft), 2)

    def test_prune_deletes_old_operational_rows_and_keeps_dimensions(self) -> None:
        ids = self._seed_dataset()

        result = prune_retained_data(
            self.session,
            sports_days=60,
            raw_ingest_days=14,
            ingest_run_days=90,
            now=ids["now"],
        )

        self.assertFalse(result.dry_run)
        self.assertEqual(result.total_deleted, 11)
        self.assertIsNone(self.session.get(Game, ids["old_game_id"]))
        self.assertIsNotNone(self.session.get(Game, ids["recent_game_id"]))
        self.assertIsNotNone(self.session.get(Player, ids["player_id"]))
        self.assertIsNotNone(self.session.get(User, ids["user_id"]))
        self.assertEqual(self._count(PlayerGameStat), 1)
        self.assertEqual(self._count(TeamGameStat), 1)
        self.assertEqual(self._count(RollingMetric), 1)
        self.assertEqual(self._count(RollingMetricBaselineSample), 1)
        self.assertEqual(self._count(Shyft), 1)
        self.assertEqual(self._count(ShyftComment), 0)
        self.assertEqual(self._count(ShyftReactionRecord), 0)
        self.assertEqual(self._count(CommentReport), 0)
        self.assertEqual(self._count(RawIngestEvent), 1)
        self.assertEqual(self._count(IngestRun), 1)

    def test_non_final_cleanup_removes_live_generated_data_but_keeps_unknown(self) -> None:
        ids = self._seed_dataset()
        now = ids["now"]

        league = self.session.execute(select(League).where(League.name == "NBA")).scalar_one()
        teams = self.session.execute(select(Team).where(Team.league_id == league.id)).scalars().all()
        player = self.session.get(Player, ids["player_id"])

        live_game = Game(
            league_id=league.id,
            game_date=now.date(),
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            external_game_id="live-game",
            status="live",
        )
        unknown_game = Game(
            league_id=league.id,
            game_date=now.date(),
            home_team_id=teams[0].id,
            away_team_id=teams[1].id,
            external_game_id="unknown-game",
            status="unknown",
        )
        self.session.add_all([live_game, unknown_game])
        self.session.flush()

        live_stat = PlayerGameStat(player_id=player.id, game_id=live_game.id, points=10)
        unknown_stat = PlayerGameStat(player_id=player.id, game_id=unknown_game.id, points=20)
        self.session.add_all([live_stat, unknown_stat])
        self.session.flush()

        live_metric = RollingMetric(
            player_id=player.id,
            game_id=live_game.id,
            source_stat_id=live_stat.id,
            metric_name="points",
            rolling_avg=20,
            rolling_stddev=3,
            z_score=-3,
            updated_at=now,
        )
        unknown_metric = RollingMetric(
            player_id=player.id,
            game_id=unknown_game.id,
            source_stat_id=unknown_stat.id,
            metric_name="points",
            rolling_avg=20,
            rolling_stddev=3,
            z_score=2,
            updated_at=now,
        )
        self.session.add_all([live_metric, unknown_metric])
        self.session.flush()

        live_shyft = Shyft(
            player_id=player.id,
            game_id=live_game.id,
            rolling_metric_id=live_metric.id,
            source_stat_id=live_stat.id,
            team_id=teams[0].id,
            league_id=league.id,
            subject_type="player",
            shyft_type="OUTLIER",
            metric_name="points",
            current_value=10,
            baseline_value=20,
            z_score=-3,
            explanation="live",
            created_at=now,
        )
        unknown_shyft = Shyft(
            player_id=player.id,
            game_id=unknown_game.id,
            rolling_metric_id=unknown_metric.id,
            source_stat_id=unknown_stat.id,
            team_id=teams[0].id,
            league_id=league.id,
            subject_type="player",
            shyft_type="OUTLIER",
            metric_name="points",
            current_value=20,
            baseline_value=10,
            z_score=2,
            explanation="unknown",
            created_at=now,
        )
        self.session.add_all([live_shyft, unknown_shyft])
        self.session.flush()
        live_game_id = live_game.id
        unknown_game_id = unknown_game.id
        live_stat_id = live_stat.id
        unknown_stat_id = unknown_stat.id
        live_shyft_id = live_shyft.id
        unknown_shyft_id = unknown_shyft.id
        self.session.commit()

        result = cleanup_non_final_generated_data(self.session)

        self.assertEqual(result.games_touched, 1)
        self.assertEqual(result.player_stats_deleted, 1)
        self.assertEqual(result.rolling_metrics_deleted, 1)
        self.assertEqual(result.shyfts_deleted, 1)
        self.assertIsNotNone(self.session.get(Game, live_game_id))
        self.assertIsNone(self.session.get(PlayerGameStat, live_stat_id))
        self.assertIsNone(self.session.get(Shyft, live_shyft_id))
        self.assertIsNotNone(self.session.get(Game, unknown_game_id))
        self.assertIsNotNone(self.session.get(PlayerGameStat, unknown_stat_id))
        self.assertIsNotNone(self.session.get(Shyft, unknown_shyft_id))

    def test_non_final_cleanup_refuses_unknown_status(self) -> None:
        self._seed_dataset()

        with self.assertRaises(ValueError):
            cleanup_non_final_generated_data(self.session, statuses=("unknown",))


if __name__ == "__main__":
    unittest.main()
