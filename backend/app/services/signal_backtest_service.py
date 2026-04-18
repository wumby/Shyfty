from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
import json
from pathlib import Path
from statistics import mean
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.signals import (
    METRICS_BY_LEAGUE,
    build_metric_snapshots,
    classify_signal,
    load_signal_threshold_payload,
    metric_success,
    recommend_thresholds_from_samples,
    score_signal,
)
from app.models.game import Game
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.services.signal_generation_service import build_signal_generation_context


@dataclass(frozen=True)
class BacktestResult:
    summary: dict[str, Any]
    signal_type_metrics: dict[str, Any]
    calibration: list[dict[str, Any]]
    thresholds: dict[str, Any]
    signal_samples: list[dict[str, Any]]


def _future_values(metric_name: str, stats: list[PlayerGameStat], start_index: int, horizon: int) -> list[float]:
    values: list[float] = []
    for stat in stats[start_index + 1 : start_index + 1 + horizon]:
        value = getattr(stat, metric_name, None)
        if value is not None:
            values.append(float(value))
    return values


def _score_bucket(score: float) -> str:
    lower = int(score // 10) * 10
    upper = min(lower + 9, 100)
    return f"{lower:02d}-{upper:02d}"


def run_signal_backtest(
    db: Session,
    *,
    horizons: tuple[int, ...] = (1, 3),
) -> BacktestResult:
    players = db.execute(
        select(Player).options(selectinload(Player.league)).order_by(Player.id)
    ).scalars().all()
    game_dates = {game_id: game_date for game_id, game_date in db.execute(select(Game.id, Game.game_date)).all()}
    context = build_signal_generation_context(db)

    signal_samples: list[dict[str, Any]] = []
    threshold_samples: dict[str, list[dict[str, float]]] = defaultdict(list)
    latest_event_date = max(game_dates.values()) if game_dates else None

    for player in players:
        stats = db.execute(
            select(PlayerGameStat)
            .join(Game, PlayerGameStat.game_id == Game.id)
            .where(PlayerGameStat.player_id == player.id)
            .order_by(Game.game_date, Game.id)
        ).scalars().all()
        if len(stats) < 4:
            continue

        metric_stats = {
            metric_name: [stat for stat in stats if getattr(stat, metric_name, None) is not None]
            for metric_name in METRICS_BY_LEAGUE[player.league.name]
        }
        usage_snapshots = {
            snapshot.game_id: snapshot
            for snapshot in build_metric_snapshots(
                "usage_rate",
                metric_stats.get("usage_rate", []),
                game_dates_by_game_id=game_dates,
            )
        } if "usage_rate" in METRICS_BY_LEAGUE[player.league.name] else {}

        for metric_name, metric_rows in metric_stats.items():
            stat_index_by_id = {stat.id: index for index, stat in enumerate(metric_rows)}
            for snapshot in build_metric_snapshots(metric_name, metric_rows, game_dates_by_game_id=game_dates):
                usage_snapshot = usage_snapshots.get(snapshot.game_id)
                contextual_snapshot = snapshot.with_context(
                    opponent_average_allowed=context.opponent_average_allowed.get((snapshot.source_stat_id, metric_name)),
                    opponent_rank=context.opponent_rank.get((snapshot.source_stat_id, metric_name)),
                    pace_proxy=context.game_pace_proxy.get(snapshot.game_id),
                    usage_shift=(
                        snapshot.current_value - snapshot.medium_window.rolling_avg
                        if metric_name == "usage_rate"
                        else (usage_snapshot.current_value - usage_snapshot.medium_window.rolling_avg) if usage_snapshot else None
                    ),
                )
                signal_type = classify_signal(contextual_snapshot, metric_name)
                if signal_type is None:
                    continue

                signal_score, _ = score_signal(
                    contextual_snapshot,
                    signal_type=signal_type,
                    event_date=contextual_snapshot.event_date,
                    latest_event_date=latest_event_date,
                )
                stat_index = stat_index_by_id.get(snapshot.source_stat_id)
                if stat_index is None:
                    continue

                outcomes: dict[str, bool] = {}
                for horizon in horizons:
                    future_values = _future_values(metric_name, metric_rows, stat_index, horizon)
                    outcomes[f"continued_{horizon}g"] = metric_success(
                        signal_type,
                        baseline_value=contextual_snapshot.baseline_value,
                        future_values=future_values,
                    )

                signal_samples.append(
                    {
                        "player_id": player.id,
                        "player_name": player.name,
                        "league": player.league.name,
                        "metric_name": metric_name,
                        "signal_type": signal_type,
                        "signal_score": round(signal_score, 1),
                        "short_z": round(contextual_snapshot.short_window.z_score, 4),
                        "medium_z": round(contextual_snapshot.medium_window.z_score, 4),
                        "season_z": round(contextual_snapshot.season_window.z_score, 4),
                        "event_date": contextual_snapshot.event_date.isoformat() if isinstance(contextual_snapshot.event_date, date) else None,
                        **outcomes,
                    }
                )
                threshold_samples[metric_name].append(
                    {
                        "short_z": abs(contextual_snapshot.short_window.z_score),
                        "medium_z": abs(contextual_snapshot.medium_window.z_score),
                        "consistency_std": contextual_snapshot.short_window.rolling_stddev,
                    }
                )

    overall_precision = mean(sample["continued_1g"] for sample in signal_samples) if signal_samples else 0.0
    multi_game_precision = mean(sample["continued_3g"] for sample in signal_samples) if signal_samples else 0.0

    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sample in signal_samples:
        by_type[sample["signal_type"]].append(sample)
        by_bucket[_score_bucket(sample["signal_score"])].append(sample)

    signal_type_metrics = {
        signal_type: {
            "count": len(samples),
            "precision_next_game": round(mean(sample["continued_1g"] for sample in samples), 4) if samples else 0.0,
            "precision_next_3_games": round(mean(sample["continued_3g"] for sample in samples), 4) if samples else 0.0,
            "avg_signal_score": round(mean(sample["signal_score"] for sample in samples), 2) if samples else 0.0,
        }
        for signal_type, samples in sorted(by_type.items())
    }

    calibration = [
        {
            "score_bucket": bucket,
            "count": len(samples),
            "outcome_rate_1g": round(mean(sample["continued_1g"] for sample in samples), 4) if samples else 0.0,
            "outcome_rate_3g": round(mean(sample["continued_3g"] for sample in samples), 4) if samples else 0.0,
        }
        for bucket, samples in sorted(by_bucket.items())
    ]

    return BacktestResult(
        summary={
            "signal_count": len(signal_samples),
            "precision_next_game": round(overall_precision, 4),
            "precision_next_3_games": round(multi_game_precision, 4),
        },
        signal_type_metrics=signal_type_metrics,
        calibration=calibration,
        thresholds={
            "active": load_signal_threshold_payload(),
            "recommended": recommend_thresholds_from_samples(threshold_samples),
        },
        signal_samples=signal_samples,
    )


def write_backtest_result(result: BacktestResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "summary": result.summary,
                "signal_type_metrics": result.signal_type_metrics,
                "calibration": result.calibration,
                "thresholds": result.thresholds,
                "signal_samples": result.signal_samples,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
