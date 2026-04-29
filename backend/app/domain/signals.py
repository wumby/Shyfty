from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
import json
import math
from statistics import mean, pstdev
from typing import Optional

from app.core.signal_config import get_signal_config, signal_config_path
METRICS_BY_LEAGUE = {
    "NBA": ["points", "rebounds", "assists", "steals", "blocks", "turnovers", "minutes_played", "usage_rate"],
    "NFL": ["passing_yards", "rushing_yards", "receiving_yards", "touchdowns"],
}

TEAM_METRICS_BY_LEAGUE = {
    "NBA": ["points", "pace", "fg_pct", "turnovers", "off_rating"],
}

BASELINE_WINDOW_SIZE = get_signal_config().windows.short_window

MIN_SIGNAL_SAMPLE_SIZE = 3
Z_SCORE_EPSILON = 1.0
LOW_FREQUENCY_STATS = {"steals", "blocks"}
VOLUME_STATS = {"points", "rebounds", "assists", "minutes", "minutes_played", "turnovers"}
MINUTES_STATS = {"minutes", "minutes_played"}
# Stats suppressed when current-game minutes are below the eligibility threshold.
# minutes_played itself is intentionally excluded so a DNP still surfaces a minutes drop.
MINUTES_GATED_STATS = {"points", "rebounds", "assists", "steals", "blocks", "turnovers", "usage_rate"}

SEVERITY_SWING_SCORE = 6.0
SEVERITY_OUTLIER_SCORE = 8.0


@dataclass(frozen=True)
class StatSignalThreshold:
    min_baseline: float
    min_delta: float
    min_z: float
    weight: float
    min_actual: Optional[float] = None


STAT_SIGNAL_CONFIG: dict[str, StatSignalThreshold] = {
    "points": StatSignalThreshold(min_baseline=8, min_delta=8, min_z=1.4, weight=1.0),
    "rebounds": StatSignalThreshold(min_baseline=4, min_delta=3, min_z=1.4, weight=0.9),
    "assists": StatSignalThreshold(min_baseline=3, min_delta=3, min_z=1.4, weight=0.9),
    "steals": StatSignalThreshold(min_baseline=0, min_actual=3, min_delta=2, min_z=1.3, weight=0.7),
    "blocks": StatSignalThreshold(min_baseline=0, min_actual=3, min_delta=2, min_z=1.3, weight=0.7),
    "turnovers": StatSignalThreshold(min_baseline=2, min_delta=2, min_z=1.3, weight=0.6),
    "minutes_played": StatSignalThreshold(min_baseline=12, min_delta=6, min_z=1.4, weight=0.7),
    "usage_rate": StatSignalThreshold(min_baseline=12, min_delta=5, min_z=1.4, weight=0.8),
    "passing_yards": StatSignalThreshold(min_baseline=120, min_delta=60, min_z=1.4, weight=0.9),
    "rushing_yards": StatSignalThreshold(min_baseline=25, min_delta=25, min_z=1.4, weight=0.8),
    "receiving_yards": StatSignalThreshold(min_baseline=25, min_delta=25, min_z=1.4, weight=0.8),
    "touchdowns": StatSignalThreshold(min_baseline=0, min_actual=2, min_delta=1, min_z=1.3, weight=0.6),
    "pace": StatSignalThreshold(min_baseline=90, min_delta=5, min_z=1.4, weight=0.6),
    "fg_pct": StatSignalThreshold(min_baseline=0.35, min_delta=0.08, min_z=1.4, weight=0.6),
    "fg3_pct": StatSignalThreshold(min_baseline=0.25, min_delta=0.10, min_z=1.4, weight=0.6),
    "off_rating": StatSignalThreshold(min_baseline=95, min_delta=10, min_z=1.4, weight=0.7),
}

DEFAULT_STAT_SIGNAL_CONFIG = StatSignalThreshold(min_baseline=1, min_delta=1, min_z=1.4, weight=0.5)


def stat_signal_config(metric_name: str) -> StatSignalThreshold:
    return STAT_SIGNAL_CONFIG.get(metric_name, DEFAULT_STAT_SIGNAL_CONFIG)


def minutes_eligible(current: float, baseline: float) -> tuple[bool, str]:
    cfg = get_signal_config().minutes_eligibility
    if current >= cfg.min_absolute:
        return True, ""
    if baseline > 0 and current >= baseline * cfg.min_fraction_of_baseline:
        return True, ""
    return False, (
        f"minutes_gate: current={current:.1f} is below min_absolute={cfg.min_absolute} "
        f"and below {cfg.min_fraction_of_baseline * 100:.0f}% of baseline={baseline:.1f}"
    )


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
    minutes_current: Optional[float] = None
    minutes_baseline: Optional[float] = None
    high_volatility: bool = False

    @property
    def delta(self) -> float:
        return self.current_value - self.baseline_value

    def with_context(
        self,
        *,
        opponent_average_allowed: Optional[float] = None,
        opponent_rank: Optional[int] = None,
        pace_proxy: Optional[float] = None,
        usage_shift: Optional[float] = None,
        minutes_current: Optional[float] = None,
        minutes_baseline: Optional[float] = None,
    ) -> "MetricSnapshot":
        thresholds = get_signal_config().thresholds
        return replace(
            self,
            opponent_average_allowed=opponent_average_allowed,
            opponent_rank=opponent_rank,
            pace_proxy=pace_proxy,
            usage_shift=usage_shift,
            minutes_current=minutes_current,
            minutes_baseline=minutes_baseline,
            high_volatility=self.volatility_index >= thresholds.high_volatility_index,
        )


def movement_pct(current: float, baseline: float) -> Optional[float]:
    if math.isclose(baseline, 0.0, abs_tol=0.05):
        return None
    return ((current - baseline) / baseline) * 100


def meaningful_movement_pct(metric_name: str, current: float, baseline: float) -> Optional[float]:
    config = stat_signal_config(metric_name)
    if baseline < config.min_baseline * 1.5:
        return None
    return movement_pct(current, baseline)


def performance_ratio(current: float, baseline: float) -> Optional[float]:
    if baseline == 0:
        return None
    return current / baseline


def deviation_from_expected(current: float, baseline: float) -> Optional[float]:
    performance = performance_ratio(current, baseline)
    if performance is None:
        return None
    return abs(performance - 1.0)


def severity_for_deviation(deviation: Optional[float]) -> Optional[str]:
    return None


def trend_direction(current: float, baseline: float) -> str:
    tolerance = max(abs(baseline) * 0.02, 0.01)
    if math.isclose(current, baseline, abs_tol=tolerance):
        return "flat"
    return "up" if current > baseline else "down"


def metric_label(metric_name: str) -> str:
    labels = {
        "points": "Points",
        "rebounds": "Rebounds",
        "assists": "Assists",
        "steals": "Steals",
        "blocks": "Blocks",
        "turnovers": "Turnovers",
        "minutes_played": "Minutes",
        "usage_rate": "Usage Rate",
        "passing_yards": "Passing Yards",
        "rushing_yards": "Rushing Yards",
        "receiving_yards": "Receiving Yards",
        "touchdowns": "Touchdowns",
        "pace": "Pace",
        "off_rating": "Offensive Rating",
        "fg_pct": "Field Goal %",
        "fg3_pct": "3PT %",
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
        "pace": "Pace",
        "off_rating": "Offensive rating",
        "fg_pct": "Shooting efficiency",
        "fg3_pct": "Three-point accuracy",
    }
    return phrases.get(metric_name, metric_name.replace("_", " ").title())


def baseline_window_label(window_size: Optional[int] = None) -> str:
    size = BASELINE_WINDOW_SIZE if window_size is None else window_size
    return f"last {size} games"


def importance_score(signal_type: str, z_score: float = 0.0, deviation: Optional[float] = None) -> float:
    type_floor = {"OUTLIER": 8.0, "SWING": 6.0, "SHIFT": 4.0}.get(signal_type, 4.0)
    return round(min(type_floor + min(abs(z_score) / 3.0, 1.0), 10.0), 1)


def importance_label(signal_type: str, z_score: float = 0.0, deviation: Optional[float] = None) -> str:
    score = importance_score(signal_type, z_score, deviation)
    if score >= 8.0:
        return "High"
    if score >= 6.0:
        return "Medium"
    return "Watch"


def importance_label_for_score(score: float) -> str:
    if score >= 8.0:
        return "High"
    if score >= 6.0:
        return "Medium"
    return "Watch"


def _window_snapshot(current_value: float, observations: list[tuple[int, int, float]], window_size: int) -> WindowSnapshot:
    baseline_observations = observations[-window_size:] or observations
    baseline_values = [value for _, _, value in baseline_observations]
    rolling_avg = mean(baseline_values)
    rolling_stddev = pstdev(baseline_values) if len(baseline_values) > 1 else 0.0
    denominator = max(rolling_stddev, Z_SCORE_EPSILON)
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


def build_metric_snapshot(metric_name: str, stats: list[object]) -> Optional[MetricSnapshot]:
    snapshots = build_metric_snapshots(metric_name, stats)
    return snapshots[-1] if snapshots else None


def build_metric_snapshots(
    metric_name: str,
    stats: list[object],
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


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


def signal_score_value(snapshot: MetricSnapshot, metric_name: str) -> float:
    config = stat_signal_config(metric_name)
    z_component = _clamp(abs(snapshot.z_score) / 3.0, 0.0, 1.0)
    delta_component = _clamp(abs(snapshot.delta) / max(config.min_delta * 2.0, 1.0), 0.0, 1.0)
    raw_score = (z_component * 0.6) + (delta_component * 0.3) + (config.weight * 0.1)
    return round(_clamp(raw_score * 10.0, 0.0, 10.0), 1)


def severity_for_score(score: float) -> str:
    if score >= SEVERITY_OUTLIER_SCORE:
        return "OUTLIER"
    if score >= SEVERITY_SWING_SCORE:
        return "SWING"
    return "SHIFT"


def signal_gate_trace(snapshot: MetricSnapshot, metric_name: str) -> dict[str, object]:
    config = stat_signal_config(metric_name)
    sample_size = snapshot.short_window.sample_size
    delta = snapshot.delta
    previous_value = snapshot.short_window.values[-1] if snapshot.short_window.values else None
    if metric_name in LOW_FREQUENCY_STATS:
        baseline_or_actual = config.min_actual is not None and snapshot.current_value >= config.min_actual
        baseline_condition_name = "actual"
    else:
        baseline_or_actual = snapshot.baseline_value >= config.min_baseline
        baseline_condition_name = "baseline"
    conditions = {
        "sample_size": sample_size >= MIN_SIGNAL_SAMPLE_SIZE,
        baseline_condition_name: baseline_or_actual,
        "delta": abs(delta) >= config.min_delta,
        "z_score": abs(snapshot.z_score) >= config.min_z,
    }
    if metric_name in MINUTES_STATS:
        conditions["minutes_guard"] = snapshot.baseline_value >= 18 or (
            previous_value is not None and previous_value >= 15
        )

    minutes_gate_reason: Optional[str] = None
    if metric_name in MINUTES_GATED_STATS and snapshot.minutes_current is not None:
        eligible, minutes_gate_reason = minutes_eligible(snapshot.minutes_current, snapshot.minutes_baseline or 0.0)
        conditions["minutes_eligible"] = eligible

    return {
        "baseline": snapshot.baseline_value,
        "actual": snapshot.current_value,
        "delta": delta,
        "z_score": snapshot.z_score,
        "sample_size": sample_size,
        "thresholds": {
            "min_sample_size": MIN_SIGNAL_SAMPLE_SIZE,
            "min_baseline": config.min_baseline,
            "min_actual": config.min_actual,
            "min_delta": config.min_delta,
            "min_z": config.min_z,
            "weight": config.weight,
            "minutes_min_baseline": 18 if metric_name in MINUTES_STATS else None,
            "minutes_min_previous": 15 if metric_name in MINUTES_STATS else None,
        },
        "stat_category": "low_frequency" if metric_name in LOW_FREQUENCY_STATS else "volume",
        "previous_value": previous_value,
        "conditions": conditions,
        "passed": all(conditions.values()),
        "minutes_gate": {
            "minutes_current": snapshot.minutes_current,
            "minutes_baseline": snapshot.minutes_baseline,
            "suppressed": not conditions.get("minutes_eligible", True),
            "reason": minutes_gate_reason,
        } if metric_name in MINUTES_GATED_STATS else None,
    }


def passes_meaningfulness_gate(snapshot: MetricSnapshot, metric_name: str) -> bool:
    return bool(signal_gate_trace(snapshot, metric_name)["passed"])


def _classify_from_snapshot(snapshot: MetricSnapshot, metric_name: str) -> Optional[str]:
    if not passes_meaningfulness_gate(snapshot, metric_name):
        return None
    return severity_for_score(signal_score_value(snapshot, metric_name))


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
        current_value=current_value if current_value is not None else baseline_value if baseline_value is not None else 0.0,
        baseline_value=baseline_value if baseline_value is not None else 0.0,
        rolling_stddev=variance,
        z_score=z_score,
        short_window=WindowSnapshot([], [baseline_value if baseline_value is not None else 0.0] * MIN_SIGNAL_SAMPLE_SIZE, baseline_value if baseline_value is not None else 0.0, variance, z_score),
        medium_window=WindowSnapshot([], [baseline_value if baseline_value is not None else 0.0] * MIN_SIGNAL_SAMPLE_SIZE, baseline_value if baseline_value is not None else 0.0, variance, z_score),
        season_window=WindowSnapshot([], [baseline_value if baseline_value is not None else 0.0] * MIN_SIGNAL_SAMPLE_SIZE, baseline_value if baseline_value is not None else 0.0, variance, z_score),
        ewma=baseline_value if baseline_value is not None else 0.0,
        recent_delta=(current_value or 0.0) - (baseline_value or 0.0),
        trend_slope=0.0,
        volatility_index=0.0,
        volatility_delta=0.0,
        usage_shift=(current_value - baseline_value) if current_value is not None and baseline_value is not None else None,
        high_volatility=False,
    )
    return _classify_from_snapshot(fallback_snapshot, metric_name)


def _classification_reason_from_snapshot(signal_type: Optional[str], snapshot: MetricSnapshot, metric_name: str) -> str:
    trace = signal_gate_trace(snapshot, metric_name)
    context_parts: list[str] = []
    if snapshot.opponent_rank is not None:
        context_parts.append(f"opponent rank={snapshot.opponent_rank}")
    if snapshot.usage_shift is not None:
        context_parts.append(f"usage shift={snapshot.usage_shift:+.2f}")
    if snapshot.high_volatility:
        context_parts.append("high volatility profile")
    suffix = f" Context: {', '.join(context_parts)}." if context_parts else ""

    thresholds = trace["thresholds"]
    if not trace["passed"]:
        failed = ", ".join(name for name, passed in trace["conditions"].items() if not passed)
        minutes_gate = trace.get("minutes_gate") or {}
        minutes_note = f" {minutes_gate['reason']}" if minutes_gate.get("suppressed") and minutes_gate.get("reason") else ""
        return (
            f"No signal: failed meaningfulness gate ({failed}).{minutes_note} "
            f"baseline={snapshot.baseline_value:.2f}, actual={snapshot.current_value:.2f}, "
            f"delta={snapshot.delta:+.2f}, z={snapshot.z_score:+.2f}; "
            f"required sample_size>={thresholds['min_sample_size']}, "
            f"delta>={thresholds['min_delta']}, z>={thresholds['min_z']}."
        )

    direction = "above" if snapshot.delta > 0 else "below"
    return (
        f"{signal_type or 'Signal'} passed meaningfulness gate: actual {snapshot.current_value:.2f} is "
        f"{abs(snapshot.delta):.2f} {direction} baseline {snapshot.baseline_value:.2f} "
        f"(z={snapshot.z_score:+.2f}, sample_size={trace['sample_size']}).{suffix}"
    )


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
    direction = "above" if snapshot.delta > 0 else "below"
    return f"{signal_type.title()} {metric} move - {abs(snapshot.delta):.1f} {direction} recent baseline"


def build_explanation(
    subject_name: str,
    metric_name: str,
    current: float,
    baseline: float,
    z_score: float,
    signal_type: Optional[str] = None,
    snapshot: Optional[MetricSnapshot] = None,
) -> str:
    metric_phrase = _metric_phrase(metric_name)
    baseline_window = BASELINE_WINDOW_SIZE
    delta = current - baseline
    direction_text = "above" if current >= baseline else "below"

    return (
        f"{metric_phrase} is {abs(delta):.1f} {direction_text} "
        f"the recent baseline over the last {baseline_window} games"
    )


def score_signal(
    snapshot: MetricSnapshot,
    *,
    signal_type: str,
    metric_name: str,
    event_date: Optional[date],
    latest_event_date: Optional[date],
) -> tuple[float, str]:
    config = stat_signal_config(metric_name)
    z_component = _clamp(abs(snapshot.z_score) / 3.0, 0.0, 1.0)
    delta_component = _clamp(abs(snapshot.delta) / max(config.min_delta * 2.0, 1.0), 0.0, 1.0)
    bounded = signal_score_value(snapshot, metric_name)
    explanation = (
        f"Score {bounded:.1f}/10 from z={abs(snapshot.z_score):.2f}, "
        f"z_component={z_component:.2f}, delta={abs(snapshot.delta):.2f}, "
        f"delta_component={delta_component:.2f}, weight={config.weight:.2f}."
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
        deviations = sorted(abs(sample.get("deviation", 0.0)) for sample in samples)
        stddevs = sorted(sample["consistency_std"] for sample in samples)
        low_index = max(0, int(len(samples) * 0.35) - 1)
        mid_index = max(0, int(len(samples) * 0.65) - 1)
        high_index = min(len(samples) - 1, int(len(samples) * 0.85))
        recommendations["metrics"][metric_name] = {
            "shift_deviation": round(deviations[low_index], 2),
            "swing_deviation": round(deviations[mid_index], 2),
            "outlier_deviation": round(deviations[high_index], 2),
            "consistency_std": round(stddevs[low_index], 2),
        }
    return recommendations


def metric_success(signal_type: str, *, baseline_value: float, future_values: list[float]) -> bool:
    if not future_values:
        return False
    future_avg = mean(future_values)
    return not math.isclose(future_avg, baseline_value, abs_tol=0.05)
