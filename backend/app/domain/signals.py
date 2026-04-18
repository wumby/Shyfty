from dataclasses import dataclass
from datetime import date
import math
from statistics import mean, pstdev
from typing import Optional

from app.models.player_game_stat import PlayerGameStat

METRICS_BY_LEAGUE = {
    "NBA": ["points", "rebounds", "assists", "usage_rate"],
    "NFL": ["passing_yards", "rushing_yards", "receiving_yards", "touchdowns", "usage_rate"],
}

BASELINE_WINDOW_SIZE = 4


@dataclass(frozen=True)
class MetricSnapshot:
    game_id: int
    source_stat_id: int
    baseline_stat_ids: list[int]
    current_value: float
    baseline_value: float
    rolling_stddev: float
    z_score: float


def classify_signal(
    z_score: float,
    variance: float,
    metric_name: str,
    current_value: Optional[float] = None,
    baseline_value: Optional[float] = None,
) -> Optional[str]:
    usage_movement = None
    if metric_name == "usage_rate" and current_value is not None and baseline_value is not None:
        usage_movement = movement_pct(current_value, baseline_value)
        if usage_movement is not None and abs(usage_movement) < 8.0:
            if variance <= 0.75 and abs(z_score) <= 0.5:
                return "CONSISTENCY"
            return None

    if abs(z_score) >= 2.5:
        return "OUTLIER"
    if z_score >= 1.5:
        return "SPIKE"
    if z_score <= -1.5:
        return "DROP"
    if metric_name == "usage_rate" and abs(z_score) >= 1.0:
        return "SHIFT"
    if variance <= 0.75 and abs(z_score) <= 0.5:
        return "CONSISTENCY"
    return None


def classification_reason(signal_type: Optional[str], z_score: float, variance: float, metric_name: str) -> str:
    if signal_type == "OUTLIER":
        return f"|z|={abs(z_score):.2f} crossed the outlier threshold of 2.50."
    if signal_type == "SPIKE":
        return f"z={z_score:.2f} finished above the spike threshold of 1.50."
    if signal_type == "DROP":
        return f"z={z_score:.2f} finished below the drop threshold of -1.50."
    if signal_type == "SHIFT":
        return f"{metric_label(metric_name)} triggered a usage shift with |z|={abs(z_score):.2f} against the 1.00 threshold."
    if signal_type == "CONSISTENCY":
        return f"Rolling variance stayed low at {variance:.2f}, below the consistency threshold of 0.75."
    return "No classification threshold was met."


def _metric_phrase(metric_name: str) -> str:
    phrases = {
        "points": "Scoring",
        "rebounds": "Rebounding",
        "assists": "Playmaking",
        "usage_rate": "Usage",
        "passing_yards": "Passing production",
        "rushing_yards": "Rushing production",
        "receiving_yards": "Receiving production",
        "touchdowns": "Touchdown output",
    }
    return phrases.get(metric_name, metric_name.replace("_", " ").title())


def metric_label(metric_name: str) -> str:
    labels = {
        "points": "Scoring",
        "rebounds": "Rebounding",
        "assists": "Playmaking",
        "usage_rate": "Usage",
        "passing_yards": "Passing Yards",
        "rushing_yards": "Rushing Yards",
        "receiving_yards": "Receiving Yards",
        "touchdowns": "Touchdowns",
    }
    return labels.get(metric_name, metric_name.replace("_", " ").title())


def baseline_window_label() -> str:
    return f"last {BASELINE_WINDOW_SIZE + 1} games"


def movement_pct(current: float, baseline: float) -> Optional[float]:
    if math.isclose(baseline, 0.0, abs_tol=0.05):
        return None
    return ((current - baseline) / baseline) * 100


def trend_direction(current: float, baseline: float) -> str:
    tolerance = max(abs(baseline) * 0.02, 0.01)
    if math.isclose(current, baseline, abs_tol=tolerance):
        return "flat"
    return "up" if current > baseline else "down"


def importance_score(signal_type: str, z_score: float) -> float:
    type_floor = {
        "OUTLIER": 85.0,
        "SPIKE": 68.0,
        "DROP": 68.0,
        "SHIFT": 58.0,
        "CONSISTENCY": 40.0,
    }.get(signal_type, 50.0)
    strength_bonus = min(abs(z_score) * 8.0, 15.0)
    return round(min(type_floor + strength_bonus, 100.0), 1)


def importance_label(signal_type: str, z_score: float) -> str:
    score = importance_score(signal_type, z_score)
    if score >= 85.0:
        return "High"
    if score >= 65.0:
        return "Medium"
    return "Watch"


def build_explanation(
    player_name: str,
    metric_name: str,
    current: float,
    baseline: float,
    z_score: float,
    signal_type: Optional[str] = None,
) -> str:
    metric_phrase = _metric_phrase(metric_name)
    baseline_window = BASELINE_WINDOW_SIZE + 1
    if signal_type == "CONSISTENCY":
        return (
            f"{metric_phrase} stayed tightly anchored to {player_name}'s recent baseline "
            f"over the last {baseline_window} games"
        )
    if signal_type == "SHIFT":
        direction_text = "up" if current >= baseline else "down"
        return f"{metric_phrase} role shifted {direction_text} against {player_name}'s recent baseline over the last {baseline_window} games"
    if math.isclose(baseline, 0.0, abs_tol=0.05):
        direction_text = "above" if current >= baseline else "below"
        return f"{metric_phrase} is {direction_text} his recent baseline over the last {baseline_window} games"

    percent_change = abs(((current - baseline) / baseline) * 100)
    rounded_change = max(1, int(round(percent_change)))
    direction_text = "above" if current >= baseline else "below"

    if abs(z_score) >= 2.5:
        qualifier = "well "
    elif abs(z_score) >= 1.5:
        qualifier = ""
    else:
        qualifier = "slightly "

    return (
        f"{metric_phrase} is {rounded_change}% {qualifier}{direction_text} "
        f"his recent baseline over the last {baseline_window} games"
    )


def build_metric_snapshot(metric_name: str, stats: list[PlayerGameStat]) -> Optional[MetricSnapshot]:
    snapshots = build_metric_snapshots(metric_name, stats)
    return snapshots[-1] if snapshots else None


def build_metric_snapshots(metric_name: str, stats: list[PlayerGameStat]) -> list[MetricSnapshot]:
    observations = [
        (stat.id, stat.game_id, float(value))
        for stat in stats
        if (value := getattr(stat, metric_name)) is not None
    ]

    snapshots: list[MetricSnapshot] = []
    for index in range(2, len(observations)):
        current_stat_id, current_game_id, current_value = observations[index]
        prior_observations = observations[:index]
        baseline_observations = prior_observations[-BASELINE_WINDOW_SIZE:] or prior_observations
        baseline_values = [value for _, _, value in baseline_observations]
        baseline_value = mean(baseline_values)
        rolling_stddev = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
        denominator = rolling_stddev if rolling_stddev > 0 else 1.0
        z_score = (current_value - baseline_value) / denominator

        snapshots.append(
            MetricSnapshot(
                game_id=current_game_id,
                source_stat_id=current_stat_id,
                baseline_stat_ids=[stat_id for stat_id, _, _ in baseline_observations],
                current_value=current_value,
                baseline_value=baseline_value,
                rolling_stddev=rolling_stddev,
                z_score=z_score,
            )
        )

    return snapshots
