import unittest

from app.domain.signals import build_metric_snapshots, classification_reason, classify_signal, importance_label
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

    def test_classify_signal_preserves_current_rules(self) -> None:
        self.assertEqual(classify_signal(2.6, 0.5, "points", 44.0, 30.25), "OUTLIER")
        self.assertEqual(classify_signal(1.7, 1.2, "points", 28.0, 26.0), "SPIKE")
        self.assertEqual(classify_signal(-1.7, 1.2, "points", 29.0, 31.0), "DROP")
        self.assertEqual(classify_signal(1.1, 1.2, "usage_rate", 38.2, 34.2), "SHIFT")
        self.assertIsNone(classify_signal(0.2, 0.5, "rebounds", 13.0, 13.0))
        self.assertIsNone(classify_signal(1.0, 0.5, "touchdowns", 3.0, 2.5))
        self.assertIsNone(classify_signal(-2.4, 0.01, "usage_rate", 0.28, 0.30))

    def test_classification_reason_and_importance_label_match_thresholds(self) -> None:
        self.assertIn("outlier threshold", classification_reason("OUTLIER", 2.6, 0.4, "points"))
        self.assertEqual(classification_reason(None, 0.2, 0.5, "rebounds"), "No classification threshold was met.")
        self.assertEqual(importance_label("OUTLIER", 2.6), "High")
        self.assertEqual(importance_label("SPIKE", 1.7), "Medium")


if __name__ == "__main__":
    unittest.main()
