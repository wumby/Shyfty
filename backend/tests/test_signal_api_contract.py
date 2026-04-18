import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.player_service import get_player_metric_series, get_player_signals
from app.services.seed_service import seed_database
from app.services.signal_inspection_service import inspect_signal
from app.services.signal_generation_service import generate_signals
from app.services.signal_service import list_signals


class SignalAPIContractTests(unittest.TestCase):
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
        seed_database(self.session)
        generate_signals(self.session)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_signal_feed_includes_presentation_fields(self) -> None:
        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=5,
        )

        self.assertTrue(page.items)
        self.assertEqual(len(page.items), 5)
        self.assertTrue(page.has_more)
        self.assertEqual(page.next_cursor, page.items[-1].id)

        signal = page.items[0]
        self.assertIsInstance(signal.importance, float)
        self.assertEqual(signal.baseline_window, "last 5 games")
        self.assertTrue(signal.metric_label)
        self.assertIn(signal.trend_direction, {"up", "down", "flat"})
        self.assertIn(signal.importance_label, {"High", "Medium", "Watch"})
        self.assertEqual(signal.summary_template, "metric_vs_recent_baseline")
        self.assertEqual(signal.summary_template_inputs.baseline_window, signal.baseline_window)
        self.assertEqual(signal.summary_template_inputs.trend_direction, signal.trend_direction)
        self.assertEqual(signal.summary_template_inputs.current_value, signal.current_value)
        self.assertEqual(signal.summary_template_inputs.baseline_value, signal.baseline_value)
        self.assertIsNotNone(signal.event_date)
        self.assertGreater(signal.game_id, 0)
        self.assertGreaterEqual(signal.rolling_stddev, 0.0)
        self.assertTrue(signal.classification_reason)

    def test_player_signals_return_same_enriched_shape(self) -> None:
        signals = get_player_signals(self.session, player_id=1)

        self.assertTrue(signals)
        signal = signals[0]
        self.assertGreaterEqual(signal.importance, 0.0)
        self.assertLessEqual(signal.importance, 100.0)
        self.assertIn(signal.trend_direction, {"up", "down", "flat"})
        self.assertEqual(signal.summary_template_inputs.movement_pct, signal.movement_pct)
        self.assertEqual(signal.summary_template_inputs.current_value, signal.current_value)

    def test_player_metric_series_include_game_id_for_signal_correlation(self) -> None:
        metrics = get_player_metric_series(self.session, player_id=1)

        self.assertTrue(metrics)
        self.assertGreater(metrics[0].game_id, 0)
        self.assertTrue(metrics[0].metrics)

    def test_signal_feed_paginates_with_before_id_cursor(self) -> None:
        first_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=3,
        )

        self.assertEqual(len(first_page.items), 3)
        self.assertTrue(first_page.has_more)
        self.assertEqual(first_page.next_cursor, first_page.items[-1].id)

        second_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=3,
            before_id=first_page.next_cursor,
        )

        self.assertEqual(len(second_page.items), 3)
        self.assertTrue(second_page.has_more)
        self.assertEqual(second_page.next_cursor, second_page.items[-1].id)
        self.assertTrue(all(signal.id < first_page.next_cursor for signal in second_page.items))
        self.assertTrue(set(signal.id for signal in first_page.items).isdisjoint(signal.id for signal in second_page.items))

    def test_signal_trace_exposes_source_stat_and_baseline_window(self) -> None:
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

        trace = inspect_signal(self.session, signal.id)

        self.assertIsNotNone(trace)
        assert trace is not None
        self.assertEqual(trace.signal.id, signal.id)
        self.assertIsNotNone(trace.rolling_metric.id)
        self.assertEqual(trace.source_stat.game_id, signal.game_id)
        self.assertGreater(trace.source_stat.stat_id, 0)
        self.assertEqual(trace.source_stat.current_value, signal.current_value)
        self.assertLessEqual(len(trace.baseline_samples), signal.baseline_window_size - 1)
        self.assertTrue(trace.baseline_samples)
        self.assertGreater(trace.baseline_samples[0].stat_id, 0)


if __name__ == "__main__":
    unittest.main()
