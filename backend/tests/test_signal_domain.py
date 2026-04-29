import unittest

from app.domain.signals import (
    build_metric_snapshots,
    classification_reason,
    classify_signal,
    importance_label,
    signal_gate_trace,
)
from app.models.player_game_stat import PlayerGameStat


class SignalDomainTests(unittest.TestCase):
    def test_build_metric_snapshots_backfills_history(self) -> None:
        stats = [
            PlayerGameStat(game_id=1, points=29),
            PlayerGameStat(game_id=2, points=31),
            PlayerGameStat(game_id=3, points=28),
            PlayerGameStat(game_id=4, points=33),
            PlayerGameStat(game_id=5, points=44),
        ]

        snapshots = build_metric_snapshots("points", stats)

        self.assertEqual(len(snapshots), 3)
        self.assertEqual([snapshot.game_id for snapshot in snapshots], [3, 4, 5])
        self.assertEqual(round(snapshots[0].baseline_value, 2), 30.0)
        self.assertEqual(round(snapshots[0].z_score, 2), -2.0)
        self.assertEqual(round(snapshots[-1].baseline_value, 2), 30.25)
        self.assertEqual(round(snapshots[-1].z_score, 2), 7.16)

    def test_classify_signal_uses_meaningfulness_gate_and_direction(self) -> None:
        self.assertEqual(classify_signal(2.6, 0.5, "points", 44.0, 20.0), "OUTLIER")
        self.assertEqual(classify_signal(-1.7, 1.2, "points", 12.0, 20.0), "SHIFT")
        self.assertIsNone(classify_signal(1.7, 1.2, "points", 27.0, 20.0))
        self.assertIsNone(classify_signal(1.1, 1.2, "usage_rate", 38.2, 34.2))
        self.assertIsNone(classify_signal(0.2, 0.5, "rebounds", 13.0, 13.0))
        self.assertIsNone(classify_signal(1.0, 0.5, "touchdowns", 3.0, 0.0))
        self.assertIsNone(classify_signal(-2.4, 0.01, "usage_rate", 0.28, 0.30))

    def test_classification_reason_and_importance_label_match_thresholds(self) -> None:
        snapshots = build_metric_snapshots(
            "points",
            [
                PlayerGameStat(game_id=1, points=20),
                PlayerGameStat(game_id=2, points=20),
                PlayerGameStat(game_id=3, points=20),
                PlayerGameStat(game_id=4, points=44),
            ],
        )
        self.assertIn("passed meaningfulness gate", classification_reason("OUTLIER", snapshots[-1], "points"))
        self.assertIn("failed meaningfulness gate", classification_reason(None, 0.2, 0.5, "rebounds"))
        self.assertEqual(importance_label("OUTLIER", 2.6), "High")
        self.assertEqual(importance_label("SWING", 1.7), "Medium")

    def test_stat_specific_gate_examples(self) -> None:
        no_rebound_signal = build_metric_snapshots(
            "rebounds",
            [
                PlayerGameStat(game_id=1, rebounds=1),
                PlayerGameStat(game_id=2, rebounds=1),
                PlayerGameStat(game_id=3, rebounds=1),
                PlayerGameStat(game_id=4, rebounds=0),
            ],
        )[-1]
        self.assertIsNone(classify_signal(no_rebound_signal, "rebounds"))

        rebound_signal = build_metric_snapshots(
            "rebounds",
            [
                PlayerGameStat(game_id=1, rebounds=5),
                PlayerGameStat(game_id=2, rebounds=5),
                PlayerGameStat(game_id=3, rebounds=5),
                PlayerGameStat(game_id=4, rebounds=12),
            ],
        )[-1]
        self.assertEqual(classify_signal(rebound_signal, "rebounds"), "OUTLIER")

        no_steal_signal = build_metric_snapshots(
            "steals",
            [
                PlayerGameStat(game_id=1, steals=0),
                PlayerGameStat(game_id=2, steals=1),
                PlayerGameStat(game_id=3, steals=0),
                PlayerGameStat(game_id=4, steals=1),
                PlayerGameStat(game_id=5, steals=2),
            ],
        )[-1]
        self.assertIsNone(classify_signal(no_steal_signal, "steals"))

        steal_signal = build_metric_snapshots(
            "steals",
            [
                PlayerGameStat(game_id=1, steals=1),
                PlayerGameStat(game_id=2, steals=1),
                PlayerGameStat(game_id=3, steals=2),
                PlayerGameStat(game_id=4, steals=2),
                PlayerGameStat(game_id=5, steals=4),
            ],
        )[-1]
        self.assertEqual(classify_signal(steal_signal, "steals"), "SWING")

    def test_refined_gate_validation_cases(self) -> None:
        no_steal_signal = build_metric_snapshots(
            "steals",
            [
                PlayerGameStat(game_id=1, steals=0.5),
                PlayerGameStat(game_id=2, steals=0.5),
                PlayerGameStat(game_id=3, steals=0.5),
                PlayerGameStat(game_id=4, steals=0),
            ],
        )[-1]
        self.assertIsNone(classify_signal(no_steal_signal, "steals"))

        no_rebound_signal = build_metric_snapshots(
            "rebounds",
            [
                PlayerGameStat(game_id=1, rebounds=2),
                PlayerGameStat(game_id=2, rebounds=2),
                PlayerGameStat(game_id=3, rebounds=2),
                PlayerGameStat(game_id=4, rebounds=0),
            ],
        )[-1]
        self.assertIsNone(classify_signal(no_rebound_signal, "rebounds"))

        assist_signal = build_metric_snapshots(
            "assists",
            [
                PlayerGameStat(game_id=1, assists=4),
                PlayerGameStat(game_id=2, assists=4),
                PlayerGameStat(game_id=3, assists=4),
                PlayerGameStat(game_id=4, assists=0),
            ],
        )[-1]
        self.assertIsNotNone(classify_signal(assist_signal, "assists"))

        minutes_signal = build_metric_snapshots(
            "minutes_played",
            [
                PlayerGameStat(game_id=1, minutes_played=20),
                PlayerGameStat(game_id=2, minutes_played=20),
                PlayerGameStat(game_id=3, minutes_played=20),
                PlayerGameStat(game_id=4, minutes_played=4),
            ],
        )[-1]
        self.assertIsNotNone(classify_signal(minutes_signal, "minutes_played"))


class MinutesGateTests(unittest.TestCase):
    """Minutes-eligibility gate suppresses box-score stats for DNP / near-zero-minute games."""

    def _make_stats(self, *, points_seq, minutes_seq):
        return [
            PlayerGameStat(game_id=i + 1, points=p, minutes_played=m)
            for i, (p, m) in enumerate(zip(points_seq, minutes_seq))
        ]

    def test_zero_minutes_suppresses_points(self):
        stats = self._make_stats(
            points_seq=[25, 30, 28, 0],
            minutes_seq=[32, 35, 33, 0],
        )
        points_snap = build_metric_snapshots("points", stats)[-1]
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        gated = points_snap.with_context(
            minutes_current=min_snap.current_value,
            minutes_baseline=min_snap.baseline_value,
        )
        self.assertIsNone(classify_signal(gated, "points"))

    def test_zero_minutes_suppresses_rebounds_and_assists(self):
        def make(seq_pts, seq_reb, seq_ast, seq_min):
            return [
                PlayerGameStat(game_id=i + 1, points=p, rebounds=r, assists=a, minutes_played=m)
                for i, (p, r, a, m) in enumerate(zip(seq_pts, seq_reb, seq_ast, seq_min))
            ]

        stats = make([25, 30, 28, 0], [8, 10, 9, 0], [6, 7, 6, 0], [32, 35, 33, 0])
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        minutes_ctx = dict(
            minutes_current=min_snap.current_value,
            minutes_baseline=min_snap.baseline_value,
        )

        for metric in ("rebounds", "assists"):
            snap = build_metric_snapshots(metric, stats)[-1]
            gated = snap.with_context(**minutes_ctx)
            self.assertIsNone(classify_signal(gated, metric), f"{metric} should be suppressed at 0 min")

    def test_zero_minutes_still_allows_minutes_signal(self):
        stats = [
            PlayerGameStat(game_id=i + 1, minutes_played=m)
            for i, m in enumerate([32, 35, 33, 0])
        ]
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        # minutes_played is not in MINUTES_GATED_STATS — gate must not apply to it
        gated = min_snap.with_context(
            minutes_current=min_snap.current_value,
            minutes_baseline=min_snap.baseline_value,
        )
        self.assertIsNotNone(classify_signal(gated, "minutes_played"))

    def test_normal_minutes_allows_stat_signal(self):
        stats = [
            PlayerGameStat(game_id=i + 1, points=p, minutes_played=30)
            for i, p in enumerate([20, 20, 20, 40])
        ]
        points_snap = build_metric_snapshots("points", stats)[-1]
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        gated = points_snap.with_context(
            minutes_current=min_snap.current_value,   # 30
            minutes_baseline=min_snap.baseline_value,
        )
        self.assertIsNotNone(classify_signal(gated, "points"))

    def test_reduced_but_eligible_minutes_not_suppressed(self):
        # 8 min with ~30 min baseline: 8 >= min_absolute=5, so eligible
        stats = [
            PlayerGameStat(game_id=i + 1, points=p, minutes_played=m)
            for i, (p, m) in enumerate([(25, 30), (30, 30), (28, 30), (0, 8)])
        ]
        points_snap = build_metric_snapshots("points", stats)[-1]
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        gated = points_snap.with_context(
            minutes_current=min_snap.current_value,   # 8
            minutes_baseline=min_snap.baseline_value,  # ~30
        )
        trace = signal_gate_trace(gated, "points")
        self.assertTrue(trace["conditions"].get("minutes_eligible", True))

    def test_very_low_minutes_suppresses_stats(self):
        # 3 min with ~30 min baseline: 3 < 5 (min_absolute) AND 3 < 7.5 (25% of 30) → suppressed
        stats = [
            PlayerGameStat(game_id=i + 1, points=p, minutes_played=m)
            for i, (p, m) in enumerate([(25, 30), (30, 30), (28, 30), (0, 3)])
        ]
        points_snap = build_metric_snapshots("points", stats)[-1]
        min_snap = build_metric_snapshots("minutes_played", stats)[-1]
        gated = points_snap.with_context(
            minutes_current=min_snap.current_value,   # 3
            minutes_baseline=min_snap.baseline_value,  # ~30
        )
        trace = signal_gate_trace(gated, "points")
        self.assertFalse(trace["conditions"]["minutes_eligible"])
        self.assertIsNotNone(trace["minutes_gate"]["reason"])
        self.assertTrue(trace["minutes_gate"]["suppressed"])
        self.assertIsNone(classify_signal(gated, "points"))

    def test_gate_trace_includes_minutes_gate_key_for_gated_stats(self):
        stats = [
            PlayerGameStat(game_id=i + 1, points=p, minutes_played=30)
            for i, p in enumerate([20, 20, 20, 40])
        ]
        snap = build_metric_snapshots("points", stats)[-1]
        gated = snap.with_context(minutes_current=30.0, minutes_baseline=30.0)
        trace = signal_gate_trace(gated, "points")
        self.assertIsNotNone(trace["minutes_gate"])
        self.assertIn("minutes_current", trace["minutes_gate"])
        self.assertIn("suppressed", trace["minutes_gate"])

    def test_gate_trace_minutes_gate_is_none_for_non_gated_stat(self):
        # passing_yards is an NFL stat, not in MINUTES_GATED_STATS
        stats = [
            PlayerGameStat(game_id=i + 1, passing_yards=p)
            for i, p in enumerate([250, 260, 255, 400])
        ]
        snap = build_metric_snapshots("passing_yards", stats)[-1]
        trace = signal_gate_trace(snap, "passing_yards")
        self.assertIsNone(trace["minutes_gate"])

    def test_no_minutes_context_does_not_apply_gate(self):
        # When minutes_current is None (no context available), gate is skipped
        stats = [
            PlayerGameStat(game_id=i + 1, points=p)
            for i, p in enumerate([20, 20, 20, 40])
        ]
        snap = build_metric_snapshots("points", stats)[-1]
        # no with_context call — minutes_current stays None
        trace = signal_gate_trace(snap, "points")
        self.assertNotIn("minutes_eligible", trace["conditions"])


if __name__ == "__main__":
    unittest.main()
