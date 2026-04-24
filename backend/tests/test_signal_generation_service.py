import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.services.signal_generation_service import SignalGenerationError, generate_signals
from app.services.signal_service import list_signals
from tests.support_fixtures import load_sample_signal_dataset


class SignalGenerationServiceTests(unittest.TestCase):
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

    def test_generate_signals_backfills_historical_contexts_and_is_idempotent(self) -> None:
        load_sample_signal_dataset(self.session)

        first_result = generate_signals(self.session)
        first_signal_count = self.session.execute(select(func.count()).select_from(Signal)).scalar_one()
        first_rolling_count = self.session.execute(select(func.count()).select_from(RollingMetric)).scalar_one()

        luka = self.session.execute(select(Player).where(Player.name == "Luka Doncic")).scalar_one()
        luka_point_signal_games = self.session.execute(
            select(Signal.game_id)
            .where(Signal.player_id == luka.id, Signal.metric_name == "points")
            .order_by(Signal.game_id)
        ).scalars().all()
        luka_point_rolling_games = self.session.execute(
            select(RollingMetric.game_id)
            .where(RollingMetric.player_id == luka.id, RollingMetric.metric_name == "points")
            .order_by(RollingMetric.game_id)
        ).scalars().all()

        second_result = generate_signals(self.session)
        second_signal_count = self.session.execute(select(func.count()).select_from(Signal)).scalar_one()
        second_rolling_count = self.session.execute(select(func.count()).select_from(RollingMetric)).scalar_one()
        distinct_signal_keys = self.session.execute(
            select(func.count()).select_from(
                select(Signal.player_id, Signal.game_id, Signal.metric_name, Signal.signal_type).distinct().subquery()
            )
        ).scalar_one()
        distinct_rolling_keys = self.session.execute(
            select(func.count()).select_from(
                select(RollingMetric.player_id, RollingMetric.game_id, RollingMetric.metric_name).distinct().subquery()
            )
        ).scalar_one()

        self.assertGreater(first_result.created_signals, 0)
        self.assertGreater(first_result.created_rolling_metrics, 0)
        self.assertEqual(luka_point_signal_games, [4, 5])
        self.assertEqual(luka_point_rolling_games, [3, 4, 5])
        self.assertEqual(first_signal_count, second_signal_count)
        self.assertEqual(first_signal_count, distinct_signal_keys)
        self.assertEqual(first_rolling_count, second_rolling_count)
        self.assertEqual(first_rolling_count, distinct_rolling_keys)
        self.assertEqual(second_result.created_signals, 0)
        self.assertEqual(second_result.created_rolling_metrics, 0)
        self.assertGreater(second_result.updated_signals, 0)
        self.assertGreater(second_result.updated_rolling_metrics, 0)

    def test_generate_signals_rolls_back_on_failure(self) -> None:
        load_sample_signal_dataset(self.session)

        with mock.patch("app.services.signal_generation_service._upsert_rolling_metric", side_effect=RuntimeError("forced failure")):
            with self.assertRaises(SignalGenerationError):
                generate_signals(self.session)

        signal_count = self.session.execute(select(func.count()).select_from(Signal)).scalar_one()
        rolling_count = self.session.execute(select(func.count()).select_from(RollingMetric)).scalar_one()

        self.assertEqual(signal_count, 0)
        self.assertEqual(rolling_count, 0)

    def test_generated_signal_enrichment_matches_computed_values(self) -> None:
        load_sample_signal_dataset(self.session)
        generate_signals(self.session)

        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
        )
        self.assertEqual(len(page.items), 1)
        self.assertTrue(page.has_more)
        self.assertEqual(page.next_cursor, page.items[0].id)

        signal = page.items[0]

        if signal.baseline_value != 0:
            expected_movement = ((signal.current_value - signal.baseline_value) / signal.baseline_value) * 100
            self.assertAlmostEqual(signal.movement_pct or 0.0, expected_movement, places=4)
        self.assertEqual(signal.summary_template_inputs.movement_pct, signal.movement_pct)
        self.assertEqual(signal.summary_template_inputs.current_value, signal.current_value)
        self.assertEqual(signal.summary_template_inputs.baseline_value, signal.baseline_value)
        self.assertTrue(signal.explanation)
        self.assertIn("baseline", signal.explanation.lower())
        self.assertTrue(signal.classification_reason)

    def test_generate_signals_persists_provenance_links(self) -> None:
        load_sample_signal_dataset(self.session)
        generate_signals(self.session)

        rolling_metric = self.session.execute(
            select(RollingMetric)
            .join(Signal, Signal.rolling_metric_id == RollingMetric.id)
            .where(RollingMetric.metric_name == "points")
            .order_by(RollingMetric.id)
        ).scalars().first()
        self.assertIsNotNone(rolling_metric)
        assert rolling_metric is not None
        self.assertIsNotNone(rolling_metric.source_stat_id)

        source_stat = self.session.execute(
            select(PlayerGameStat).where(PlayerGameStat.id == rolling_metric.source_stat_id)
        ).scalar_one()
        self.assertEqual(source_stat.player_id, rolling_metric.player_id)
        self.assertEqual(source_stat.game_id, rolling_metric.game_id)

        baseline_samples = self.session.execute(
            select(RollingMetricBaselineSample)
            .where(RollingMetricBaselineSample.rolling_metric_id == rolling_metric.id)
            .order_by(RollingMetricBaselineSample.sample_order)
        ).scalars().all()
        self.assertGreaterEqual(len(baseline_samples), 2)

        signal = self.session.execute(
            select(Signal)
            .where(
                Signal.player_id == rolling_metric.player_id,
                Signal.game_id == rolling_metric.game_id,
                Signal.metric_name == rolling_metric.metric_name,
            )
        ).scalars().first()
        self.assertIsNotNone(signal)
        assert signal is not None
        self.assertEqual(signal.rolling_metric_id, rolling_metric.id)
        self.assertEqual(signal.source_stat_id, rolling_metric.source_stat_id)

    def test_generate_signals_creates_team_signal_from_real_team_stats(self) -> None:
        league = League(name="NBA")
        self.session.add(league)
        self.session.flush()

        mavs = Team(name="Dallas Mavericks", league_id=league.id, source_system="nba_stats", source_id="1610612742")
        suns = Team(name="Phoenix Suns", league_id=league.id, source_system="nba_stats", source_id="1610612756")
        self.session.add_all([mavs, suns])
        self.session.flush()

        games = [
            Game(league_id=league.id, game_date=date(2025, 1, 1), season="2024-25", home_team_id=mavs.id, away_team_id=suns.id, source_system="nba_stats", source_id="g1"),
            Game(league_id=league.id, game_date=date(2025, 1, 3), season="2024-25", home_team_id=suns.id, away_team_id=mavs.id, source_system="nba_stats", source_id="g2"),
            Game(league_id=league.id, game_date=date(2025, 1, 5), season="2024-25", home_team_id=mavs.id, away_team_id=suns.id, source_system="nba_stats", source_id="g3"),
        ]
        self.session.add_all(games)
        self.session.flush()

        self.session.add_all(
            [
                TeamGameStat(team_id=mavs.id, game_id=games[0].id, opponent_team_id=suns.id, opponent_name=suns.name, home_away="vs", points=100, rebounds=42, assists=24, fg_pct=0.48, fg3_pct=0.36, turnovers=12, pace=99.5, off_rating=108.2, source_system="nba_stats", source_game_id="g1", source_team_id="1610612742"),
                TeamGameStat(team_id=mavs.id, game_id=games[1].id, opponent_team_id=suns.id, opponent_name=suns.name, home_away="@", points=102, rebounds=41, assists=25, fg_pct=0.47, fg3_pct=0.35, turnovers=13, pace=100.1, off_rating=109.0, source_system="nba_stats", source_game_id="g2", source_team_id="1610612742"),
                TeamGameStat(team_id=mavs.id, game_id=games[2].id, opponent_team_id=suns.id, opponent_name=suns.name, home_away="vs", points=140, rebounds=45, assists=33, fg_pct=0.58, fg3_pct=0.44, turnovers=9, pace=104.9, off_rating=129.8, source_system="nba_stats", source_game_id="g3", source_team_id="1610612742"),
            ]
        )
        self.session.commit()

        result = generate_signals(self.session)

        self.assertGreater(result.created_signals, 0)
        signal = self.session.execute(
            select(Signal).where(Signal.subject_type == "team", Signal.team_id == mavs.id)
        ).scalar_one()
        self.assertIsNone(signal.player_id)
        self.assertEqual(signal.metric_name, "points")
        self.assertEqual(signal.signal_type, "SHIFT")
        self.assertIsNotNone(signal.source_team_stat_id)


if __name__ == "__main__":
    unittest.main()
