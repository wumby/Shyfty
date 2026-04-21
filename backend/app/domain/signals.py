from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import json
import math
from statistics import mean, pstdev
from typing import Optional

from app.core.signal_config import get_signal_config, signal_config_path
from app.models.player_game_stat import PlayerGameStat

METRICS_BY_LEAGUE = {
    "NBA": ["points", "rebounds", "assists", "steals", "blocks", "turnovers", "minutes_played", "usage_rate"],
    "NFL": ["passing_yards", "rushing_yards", "receiving_yards", "touchdowns", "usage_rate"],
}

BASELINE_WINDOW_SIZE = get_signal_config().windows.short_window


@dataclass(frozen=True)
class WindowSnapshot:
    stat_ids: list[int]
    values: list[float]
    rolling_avg: float
    rolling_stddev: float
    z_score: float

    @property
    def sample_size(self) -> int:
        return len(self.values)


@dataclass(frozen=True)
class MetricSnapshot:
    game_id: int
    source_stat_id: int
    event_date: Optional[date]
    baseline_stat_ids: list[int]
    current_value: float
    baseline_value: float
    rolling_stddev: float
    z_score: float
    short_window: WindowSnapshot
    medium_window: WindowSnapshot
    season_window: WindowSnapshot
    ewma: float
    recent_delta: float
    trend_slope: float
    volatility_index: float
    volatility_delta: float
    opponent_average_allowed: Optional[float] = None
    opponent_rank: Optional[int] = None
    pace_proxy: Optional[float] = None
    usage_shift: Optional[float] = None
    high_volatility: bool = False

    def with_context(
        self,
        *,
        opponent_average_allowed: Optional[float] = None,
        opponent_rank: Optional[int] = None,
        pace_proxy: Optional[float] = None,
        usage_shift: Optional[float] = None,
    ) -> "MetricSnapshot":
        thresholds = get_signal_config().thresholds
        return replace(
            self,
            opponent_average_allowed=opponent_average_allowed,
            opponent_rank=opponent_rank,
            pace_proxy=pace_proxy,
            usage_shift=usage_shift,
            high_volatility=self.volatility_index >= thresholds.high_volatility_index,
        )


def movement_pct(current: float, baseline: float) -> Optional[float]:
    if math.isclose(baseline, 0.0, abs_tol=0.05):
        return None
    return ((current - baseline) / baseline) * 100


def trend_direction(current: float, baseline: float) -> str:
    tolerance = max(abs(baseline) * 0.02, 0.01)
    if math.isclose(current, baseline, abs_tol=tolerance):
        return "flat"
    return "up" if current > baseline else "down"


def metric_label(metric_name: str) -> str:
    labels = {
        "points": "Scoring",
        "rebounds": "Rebounding",
        "assists": "Playmaking",
        "steals": "Steals",
        "blocks": "Blocks",
        "turnovers": "Turnovers",
        "minutes_played": "Minutes",
        "usage_rate": "Usage",
        "passing_yards": "Passing Yards",
        "rushing_yards": "Rushing Yards",
        "receiving_yards": "Receiving Yards",
        "touchdowns": "Touchdowns",
    }
    return labels.get(metric_name, metric_name.replace("_", " ").title())


def _metric_phrase(metric_name: str) -> str:
    phrases = {
        "points": "Scoring",
        "rebounds": "Rebounding",
        "assists": "Playmaking",
        "steals": "Defensive activity",
        "blocks": "Shot-blocking",
        "turnovers": "Ball security",
        "minutes_played": "Minutes",
        "usage_rate": "Usage",
        "passing_yards": "Passing production",
        "rushing_yards": "Rushing production",
        "receiving_yards": "Receiving production",
        "touchdowns": "Touchdown output",
    }
    return phrases.get(metric_name, metric_name.replace("_", " ").title())


def baseline_window_label(window_size: Optional[int] = None) -> str:
    size = BASELINE_WINDOW_SIZE if window_size is None else window_size
    return f"last {size + 1} games"


def importance_score(signal_type: str, z_score: float) -> float:
    type_floor = {
        "OUTLIER": 85.0,
        "SPIKE": 68.0,
        "DROP": 68.0,
        "SHIFT": 58.0,
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


def importance_label_for_score(score: float) -> str:
    if score >= 80.0:
        return "High"
    if score >= 60.0:
        return "Medium"
    return "Watch"


def _window_snapshot(current_value: float, observations: list[tuple[int, int, float]], window_size: int) -> WindowSnapshot:
    baseline_observations = observations[-window_size:] or observations
    baseline_values = [value for _, _, value in baseline_observations]
    rolling_avg = mean(baseline_values)
    rolling_stddev = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
    denominator = rolling_stddev if rolling_stddev > 0 else 1.0
    z_score = (current_value - rolling_avg) / denominator
    return WindowSnapshot(
        stat_ids=[stat_id for stat_id, _, _ in baseline_observations],
        values=baseline_values,
        rolling_avg=rolling_avg,
        rolling_stddev=rolling_stddev,
        z_score=z_score,
    )


def _ewma(values: list[float], alpha: float) -> float:
    if not values:
        return 0.0
    smoothed = values[0]
    for value in values[1:]:
        smoothed = alpha * value + (1 - alpha) * smoothed
    return smoothed


def _recent_delta(current_value: float, prior_values: list[float], delta_window: int) -> float:
    if not prior_values:
        return 0.0
    anchor = prior_values[-delta_window] if len(prior_values) >= delta_window else prior_values[0]
    return current_value - anchor


def _trend_slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    xs = list(range(len(values)))
    x_mean = mean(xs)
    y_mean = mean(values)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, values))
    denominator = sum((x - x_mean) ** 2 for x in xs)
    if math.isclose(denominator, 0.0):
        return 0.0
    return numerator / denominator


def _volatility_index(short_stddev: float, medium_stddev: float) -> float:
    if medium_stddev <= 0.0:
        return short_stddev
    return short_stddev / medium_stddev


def build_metric_snapshot(metric_name: str, stats: list[PlayerGameStat]) -> Optional[MetricSnapshot]:
    snapshots = build_metric_snapshots(metric_name, stats)
    return snapshots[-1] if snapshots else None


def build_metric_snapshots(
    metric_name: str,
    stats: list[PlayerGameStat],
    *,
    game_dates_by_game_id: Optional[dict[int, date]] = None,
) -> list[MetricSnapshot]:
    windows = get_signal_config().windows
    observations = [
        (stat.id, stat.game_id, float(value))
        for stat in stats
        if (value := getattr(stat, metric_name)) is not None
    ]

    snapshots: list[MetricSnapshot] = []
    for index in range(2, len(observations)):
        current_stat_id, current_game_id, current_value = observations[index]
        prior_observations = observations[:index]
        prior_values = [value for _, _, value in prior_observations]

        short_window = _window_snapshot(current_value, prior_observations, windows.short_window)
        medium_window = _window_snapshot(current_value, prior_observations, windows.medium_window)
        season_window = _window_snapshot(current_value, prior_observations, len(prior_observations))

        snapshots.append(
            MetricSnapshot(
                game_id=current_game_id,
                source_stat_id=current_stat_id,
                event_date=game_dates_by_game_id.get(current_game_id) if game_dates_by_game_id else None,
                baseline_stat_ids=short_window.stat_ids,
                current_value=current_value,
                baseline_value=short_window.rolling_avg,
                rolling_stddev=short_window.rolling_stddev,
                z_score=short_window.z_score,
                short_window=short_window,
                medium_window=medium_window,
                season_window=season_window,
                ewma=_ewma(prior_values, windows.ewma_alpha),
                recent_delta=_recent_delta(current_value, prior_values, windows.delta_window),
                trend_slope=_trend_slope((prior_values + [current_value])[-max(windows.trend_window, 2) :]),
                volatility_index=_volatility_index(short_window.rolling_stddev, medium_window.rolling_stddev),
                volatility_delta=short_window.rolling_stddev - medium_window.rolling_stddev,
            )
        )

    return snapshots


def multi_window_agreement(snapshot: MetricSnapshot) -> float:
    z_scores = [snapshot.short_window.z_score, snapshot.medium_window.z_score, snapshot.season_window.z_score]
    active = [z for z in z_scores if not math.isclose(z, 0.0, abs_tol=0.01)]
    if not active:
        return 0.0
    positive = sum(z > 0 for z in active)
    negative = sum(z < 0 for z in active)
    return max(positive, negative) / len(active)


def _classify_from_snapshot(snapshot: MetricSnapshot, metric_name: str) -> Optional[str]:
    thresholds = get_signal_config().thresholds_for_metric(metric_name)
    short_z = snapshot.short_window.z_score
    usage_movement = None
    if metric_name == "usage_rate":
        usage_movement = movement_pct(snapshot.current_value, snapshot.medium_window.rolling_avg)
        if usage_movement is not None and abs(usage_movement) < thresholds.usage_shift_pct:
            return None

    if max(abs(short_z), abs(snapshot.medium_window.z_score)) >= thresholds.outlier_z:
        return "OUTLIER"
    if short_z >= thresholds.spike_z:
        return "SPIKE"
    if short_z <= thresholds.drop_z:
        return "DROP"
    if metric_name == "usage_rate" and abs(short_z) >= thresholds.shift_z:
        return "SHIFT"
    return None


def classify_signal(
    snapshot_or_z_score,
    variance_or_metric_name,
    metric_name: Optional[str] = None,
    current_value: Optional[float] = None,
    baseline_value: Optional[float] = None,
) -> Optional[str]:
    if isinstance(snapshot_or_z_score, MetricSnapshot):
        return _classify_from_snapshot(snapshot_or_z_score, str(variance_or_metric_name))

    z_score = float(snapshot_or_z_score)
    variance = float(variance_or_metric_name)
    metric_name = str(metric_name)
    fallback_snapshot = MetricSnapshot(
        game_id=0,
        source_stat_id=0,
        event_date=None,
        baseline_stat_ids=[],
        current_value=current_value or baseline_value or 0.0,
        baseline_value=baseline_value or 0.0,
        rolling_stddev=variance,
        z_score=z_score,
        short_window=WindowSnapshot([], [], baseline_value or 0.0, variance, z_score),
        medium_window=WindowSnapshot([], [], baseline_value or 0.0, variance, z_score),
        season_window=WindowSnapshot([], [], baseline_value or 0.0, variance, z_score),
        ewma=baseline_value or 0.0,
        recent_delta=(current_value or 0.0) - (baseline_value or 0.0),
        trend_slope=0.0,
        volatility_index=0.0,
        volatility_delta=0.0,
        usage_shift=(current_value - baseline_value) if current_value is not None and baseline_value is not None else None,
        high_volatility=False,
    )
    return _classify_from_snapshot(fallback_snapshot, metric_name)


def _classification_reason_from_snapshot(signal_type: Optional[str], snapshot: MetricSnapshot, metric_name: str) -> str:
    thresholds = get_signal_config().thresholds_for_metric(metric_name)
    short_z = snapshot.short_window.z_score
    medium_z = snapshot.medium_window.z_score
    season_z = snapshot.season_window.z_score
    context_parts: list[str] = []
    if snapshot.opponent_rank is not None:
        context_parts.append(f"opponent rank={snapshot.opponent_rank}")
    if snapshot.usage_shift is not None:
        context_parts.append(f"usage shift={snapshot.usage_shift:+.2f}")
    if snapshot.high_volatility:
        context_parts.append("high volatility profile")
    suffix = f" Context: {', '.join(context_parts)}." if context_parts else ""

    if signal_type == "OUTLIER":
        return (
            f"Short |z|={abs(short_z):.2f} or medium |z|={abs(medium_z):.2f} crossed the outlier threshold "
            f"of {thresholds.outlier_z:.2f}; season z={season_z:.2f}.{suffix}"
        )
    if signal_type == "SPIKE":
        return (
            f"Short z={short_z:.2f} cleared the spike threshold of {thresholds.spike_z:.2f}; "
            f"medium z={medium_z:.2f}, season z={season_z:.2f}.{suffix}"
        )
    if signal_type == "DROP":
        return (
            f"Short z={short_z:.2f} cleared the drop threshold of {thresholds.drop_z:.2f}; "
            f"medium z={medium_z:.2f}, season z={season_z:.2f}.{suffix}"
        )
    if signal_type == "SHIFT":
        usage_shift = snapshot.usage_shift or 0.0
        return (
            f"{metric_label(metric_name)} triggered a role shift with short |z|={abs(short_z):.2f}, "
            f"medium z={medium_z:.2f}, usage shift={usage_shift:+.2f}.{suffix}"
        )
    return "No classification threshold was met."


def classification_reason(
    signal_type: Optional[str],
    snapshot_or_z_score,
    variance_or_metric_name,
    metric_name: Optional[str] = None,
) -> str:
    if isinstance(snapshot_or_z_score, MetricSnapshot):
        return _classification_reason_from_snapshot(signal_type, snapshot_or_z_score, str(variance_or_metric_name))

    z_score = float(snapshot_or_z_score)
    variance = float(variance_or_metric_name)
    metric_name = str(metric_name)
    fallback_snapshot = MetricSnapshot(
        game_id=0,
        source_stat_id=0,
        event_date=None,
        baseline_stat_ids=[],
        current_value=0.0,
        baseline_value=0.0,
        rolling_stddev=variance,
        z_score=z_score,
        short_window=WindowSnapshot([], [], 0.0, variance, z_score),
        medium_window=WindowSnapshot([], [], 0.0, variance, z_score),
        season_window=WindowSnapshot([], [], 0.0, variance, z_score),
        ewma=0.0,
        recent_delta=0.0,
        trend_slope=0.0,
        volatility_index=0.0,
        volatility_delta=0.0,
        high_volatility=False,
    )
    return _classification_reason_from_snapshot(signal_type, fallback_snapshot, metric_name)


def build_narrative_summary(
    signal_type: str,
    snapshot: MetricSnapshot,
    metric_name: str,
) -> str:
    """Punchy, emotionally compelling one-liner for card display."""
    metric = _metric_phrase(metric_name).lower()
    metric_title = _metric_phrase(metric_name)
    az = abs(snapshot.z_score)
    medium_z = snapshot.medium_window.z_score
    trend = snapshot.trend_slope or 0.0

    if signal_type == "SPIKE":
        if az >= 3.5:
            return f"Career-level {metric} burst — extreme outlier vs. any window"
        if az >= 2.5 and medium_z > 1.5:
            return f"Sharpest {metric} surge in recent games — trend accelerating"
        if az >= 2.5:
            return f"Explosive {metric} performance — largest spike in the window"
        if az >= 1.5:
            return f"Strong {metric} output — well above recent trend"
        return f"Above-average {metric} game — holds vs. baseline"

    if signal_type == "DROP":
        if az >= 3.5:
            return f"Sharpest {metric} collapse in recent games — role shrinking fast"
        if az >= 2.5 and medium_z < -1.5:
            return f"Extended {metric} decline — sustained multi-game pattern"
        if az >= 2.5:
            return f"Significant {metric} drop — worst in recent stretch"
        if az >= 1.5:
            return f"Below-trend {metric} — flagged for continued pattern"
        return f"Soft {metric} output — worth watching"

    if signal_type == "SHIFT":
        if snapshot.z_score > 0:
            if trend > 0.02:
                return f"Sustained {metric} role expansion — upward trend confirmed"
            return f"{metric_title} trending higher from recent baseline"
        else:
            if trend < -0.02:
                return f"{metric_title} role contracting — extended downward pattern"
            return f"{metric_title} shifted below recent baseline"

    if signal_type == "OUTLIER":
        if az >= 4.0:
            return f"Historic {metric} outlier — unprecedented vs. any window"
        if az >= 3.0:
            return f"Extreme {metric} outlier — well outside all windows"
        return f"Unusual {metric} outlier — flagged across multiple windows"

    return f"Unusual {metric} signal detected"


def build_explanation(
    player_name: str,
    metric_name: str,
    current: float,
    baseline: float,
    z_score: float,
    signal_type: Optional[str] = None,
    snapshot: Optional[MetricSnapshot] = None,
) -> str:
    metric_phrase = _metric_phrase(metric_name)
    baseline_window = BASELINE_WINDOW_SIZE + 1
    if signal_type == "SHIFT":
        direction_text = "up" if current >= baseline else "down"
        usage_text = ""
        if snapshot is not None and snapshot.usage_shift is not None:
            usage_text = f" with usage moving {snapshot.usage_shift:+.1f} points versus the medium window"
        return (
            f"{metric_phrase} role shifted {direction_text} against {player_name}'s recent baseline "
            f"over the last {baseline_window} games{usage_text}"
        )
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


def score_signal(
    snapshot: MetricSnapshot,
    *,
    signal_type: str,
    event_date: Optional[date],
    latest_event_date: Optional[date],
) -> tuple[float, str]:
    scoring = get_signal_config().scoring
    agreement = multi_window_agreement(snapshot)
    recency_days = (latest_event_date - event_date).days if latest_event_date and event_date else 0
    recency_factor = max(0.0, 1.0 - max(recency_days, 0) / 7.0)
    normalized_trend = abs(snapshot.recent_delta) / max(snapshot.medium_window.rolling_stddev, 1.0)
    volatility_penalty = max(snapshot.volatility_index - 1.0, 0.0) * scoring.volatility_penalty
    short_strength = 1.0 - math.exp(-abs(snapshot.short_window.z_score))
    medium_strength = 1.0 - math.exp(-abs(snapshot.medium_window.z_score))
    season_strength = 1.0 - math.exp(-abs(snapshot.season_window.z_score))

    score = (
        scoring.base_score
        + short_strength * scoring.short_z_weight
        + medium_strength * scoring.medium_z_weight
        + season_strength * scoring.season_z_weight
        + agreement * scoring.agreement_bonus
        + min(normalized_trend, 2.0) * scoring.trend_weight
        + recency_factor * scoring.recency_bonus
        - min(volatility_penalty, 24.0)
    )
    if signal_type == "SHIFT":
        score *= 0.9

    bounded = round(max(0.0, min(score, scoring.max_score)), 1)
    explanation = (
        f"Score {bounded:.1f} from short/medium/season z ({snapshot.short_window.z_score:+.2f}, "
        f"{snapshot.medium_window.z_score:+.2f}, {snapshot.season_window.z_score:+.2f}), "
        f"agreement={agreement:.2f}, trend={snapshot.trend_slope:+.2f}, "
        f"volatility penalty={min(volatility_penalty, 24.0):.1f}."
    )
    return bounded, explanation


def load_signal_threshold_payload() -> dict[str, object]:
    path = signal_config_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def recommend_thresholds_from_samples(samples_by_metric: dict[str, list[dict[str, float]]]) -> dict[str, object]:
    recommendations: dict[str, object] = {"metrics": {}}
    for metric_name, samples in samples_by_metric.items():
        if len(samples) < 5:
            continue
        short_scores = sorted(sample["short_z"] for sample in samples)
        medium_scores = sorted(sample["medium_z"] for sample in samples)
        stddevs = sorted(sample["consistency_std"] for sample in samples)
        low_index = max(0, int(len(samples) * 0.35) - 1)
        mid_index = max(0, int(len(samples) * 0.65) - 1)
        high_index = min(len(samples) - 1, int(len(samples) * 0.85))
        recommendations["metrics"][metric_name] = {
            "spike_z": round(short_scores[mid_index], 2),
            "outlier_z": round(short_scores[high_index], 2),
            "shift_z": round(medium_scores[mid_index], 2),
            "consistency_std": round(stddevs[low_index], 2),
        }
    return recommendations


def metric_success(signal_type: str, *, baseline_value: float, future_values: list[float]) -> bool:
    if not future_values:
        return False
    future_avg = mean(future_values)
    if signal_type in {"SPIKE", "OUTLIER", "SHIFT"}:
        return future_avg >= baseline_value
    if signal_type == "DROP":
        return future_avg <= baseline_value
    return False
