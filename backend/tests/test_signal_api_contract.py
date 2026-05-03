import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.signal_reaction import SignalReaction
from app.models.user import User
from app.models.user_follow import UserFollow
from app.services.comment_service import create_comment, list_comments
from app.services.player_service import get_player_metric_series, get_player_signals
from app.services.signal_inspection_service import inspect_signal
from app.services.signal_generation_service import generate_signals
from app.services.signal_service import FEED_MODE_FOLLOWING, list_signals
from tests.support_fixtures import load_sample_signal_dataset


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
        load_sample_signal_dataset(self.session)
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
        self.assertFalse(page.has_more)
        self.assertIsNone(page.next_cursor)

        signal = page.items[0]
        self.assertIn(signal.severity, {"OUTLIER", "SWING", "SHIFT"})
        self.assertEqual(signal.severity, signal.signal_type)
        self.assertIsNotNone(signal.performance)
        self.assertIsNotNone(signal.deviation)
        self.assertIsInstance(signal.importance, float)
        self.assertGreaterEqual(signal.signal_score, 0.0)
        self.assertLessEqual(signal.signal_score, 10.0)
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
        self.assertTrue(signal.debug_trace.passed)

    def test_player_signals_return_same_enriched_shape(self) -> None:
        signals = get_player_signals(self.session, player_id=1)

        self.assertTrue(signals)
        signal = signals[0]
        self.assertGreaterEqual(signal.importance, 0.0)
        self.assertLessEqual(signal.importance, 10.0)
        self.assertGreaterEqual(signal.signal_score, 0.0)
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

        self.assertEqual(len(second_page.items), 1)
        self.assertFalse(second_page.has_more)
        self.assertIsNone(second_page.next_cursor)
        self.assertTrue(all(signal.id < first_page.next_cursor for signal in second_page.items))
        self.assertTrue(set(signal.id for signal in first_page.items).isdisjoint(signal.id for signal in second_page.items))

    def test_comments_are_counted_across_signal_card_group(self) -> None:
        user = User(email="commenter@example.com", password_hash="hash")
        self.session.add(user)
        self.session.flush()

        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=20,
        )
        grouped: dict[tuple[str, int, int], list] = {}
        for signal in page.items:
            key = (signal.subject_type or "player", signal.player_id or signal.team_id, signal.game_id)
            grouped.setdefault(key, []).append(signal)
        group = next((signals for signals in grouped.values() if len(signals) > 1), None)
        if group is None:
            self.skipTest("Sample dataset did not generate multiple signals for one card group.")

        create_comment(self.session, signal_id=group[-1].id, user_id=user.id, body="group-level comment")

        refreshed = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=20,
        )
        refreshed_by_id = {signal.id: signal for signal in refreshed.items}
        self.assertTrue(all(refreshed_by_id[signal.id].comment_count == 1 for signal in group))
        self.assertEqual(len(list_comments(self.session, signal_id=group[0].id, current_user_id=user.id)), 1)

    def test_following_feed_ignores_engagement_when_user_has_no_follows(self) -> None:
        user = User(email="viewer@example.com", password_hash="hash")
        self.session.add(user)
        self.session.flush()

        signal = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
        ).items[0]
        self.session.add(SignalReaction(user_id=user.id, signal_id=signal.id, type="agree"))
        self.session.commit()

        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=5,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )

        self.assertEqual(page.items, [])
        self.assertFalse(page.has_more)

    def test_following_feed_only_uses_explicit_follows(self) -> None:
        user = User(email="follower@example.com", password_hash="hash")
        self.session.add(user)
        self.session.flush()

        all_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
        )
        target = next(signal for signal in all_page.items if signal.player_id is not None)
        other = next(signal for signal in all_page.items if signal.player_id != target.player_id)
        self.session.add(SignalReaction(user_id=user.id, signal_id=other.id, type="agree"))
        self.session.add(UserFollow(user_id=user.id, entity_type="player", entity_id=target.player_id))
        self.session.commit()

        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )

        self.assertTrue(page.items)
        self.assertTrue(all(signal.player_id == target.player_id for signal in page.items))
        self.assertNotIn(other.id, {signal.id for signal in page.items})

    def test_team_follow_does_not_include_team_player_signals(self) -> None:
        user = User(email="team-follower@example.com", password_hash="hash")
        self.session.add(user)
        self.session.flush()

        all_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
        )
        player_signal = next(signal for signal in all_page.items if signal.subject_type == "player")
        self.session.add(UserFollow(user_id=user.id, entity_type="team", entity_id=player_signal.team_id))
        self.session.commit()

        page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )

        self.assertTrue(all(signal.subject_type == "team" for signal in page.items))
        self.assertNotIn(player_signal.id, {signal.id for signal in page.items})

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
        self.assertLessEqual(len(trace.baseline_samples), signal.baseline_window_size)
        self.assertTrue(trace.baseline_samples)
        self.assertGreater(trace.baseline_samples[0].stat_id, 0)
        self.assertGreaterEqual(trace.rolling_metric.short_window.sample_size, 1)
        self.assertGreaterEqual(trace.rolling_metric.medium_window.sample_size, 1)
        self.assertGreaterEqual(trace.rolling_metric.season_window.sample_size, 1)
        self.assertIsNotNone(trace.signal.score_explanation)


if __name__ == "__main__":
    unittest.main()
