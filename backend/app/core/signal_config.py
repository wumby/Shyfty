from __future__ import annotations

from dataclasses import dataclass, replace
import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SignalWindows:
    short_window: int = 5
    medium_window: int = 10
    delta_window: int = 3
    trend_window: int = 5
    ewma_alpha: float = 0.4


@dataclass(frozen=True)
class SignalThresholds:
    shift_deviation: float = 0.10
    swing_deviation: float = 0.40
    outlier_deviation: float = 0.80
    consistency_std: float = 0.75
    high_volatility_index: float = 1.35


@dataclass(frozen=True)
class SignalScoring:
    base_score: float = 24.0
    short_z_weight: float = 15.0
    medium_z_weight: float = 10.0
    season_z_weight: float = 6.0
    agreement_bonus: float = 14.0
    trend_weight: float = 6.0
    recency_bonus: float = 10.0
    volatility_penalty: float = 12.0
    max_score: float = 100.0


@dataclass(frozen=True)
class MinutesEligibilityConfig:
    min_absolute: float = 5.0
    min_fraction_of_baseline: float = 0.25


@dataclass(frozen=True)
class SignalConfig:
    windows: SignalWindows = SignalWindows()
    thresholds: SignalThresholds = SignalThresholds()
    scoring: SignalScoring = SignalScoring()
    metric_thresholds: dict[str, SignalThresholds] | None = None
    minutes_eligibility: MinutesEligibilityConfig = MinutesEligibilityConfig()

    def thresholds_for_metric(self, metric_name: str) -> SignalThresholds:
        if not self.metric_thresholds:
            return self.thresholds
        return self.metric_thresholds.get(metric_name, self.thresholds)


def signal_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "signal_engine.json"


def _merge_dataclass(instance: Any, raw: dict[str, Any]) -> Any:
    if not raw:
        return instance
    values = {key: raw[key] for key in instance.__dataclass_fields__ if key in raw}
    return replace(instance, **values)


@lru_cache(maxsize=1)
def get_signal_config() -> SignalConfig:
    path = signal_config_path()
    if not path.exists():
        return SignalConfig()

    payload = json.loads(path.read_text(encoding="utf-8"))
    windows = _merge_dataclass(SignalWindows(), payload.get("windows", {}))
    thresholds = _merge_dataclass(SignalThresholds(), payload.get("thresholds", {}).get("global", {}))
    scoring = _merge_dataclass(SignalScoring(), payload.get("scoring", {}))
    minutes_eligibility = _merge_dataclass(MinutesEligibilityConfig(), payload.get("minutes_eligibility", {}))

    metric_thresholds: dict[str, SignalThresholds] = {}
    for metric_name, raw_thresholds in payload.get("thresholds", {}).get("metrics", {}).items():
        metric_thresholds[metric_name] = _merge_dataclass(thresholds, raw_thresholds)

    return SignalConfig(
        windows=windows,
        thresholds=thresholds,
        scoring=scoring,
        metric_thresholds=metric_thresholds,
        minutes_eligibility=minutes_eligibility,
    )


def reload_signal_config() -> SignalConfig:
    get_signal_config.cache_clear()
    return get_signal_config()
