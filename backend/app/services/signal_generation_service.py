from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.signals import METRICS_BY_LEAGUE, build_explanation, build_metric_snapshots, classify_signal
from app.models.game import Game
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal


@dataclass(frozen=True)
class SignalGenerationResult:
    created_signals: int = 0
    updated_signals: int = 0
    deleted_signals: int = 0
    created_rolling_metrics: int = 0
    updated_rolling_metrics: int = 0
    deleted_rolling_metrics: int = 0


class SignalGenerationError(RuntimeError):
    def __init__(self, message: str, *, partial_result: SignalGenerationResult, cause: Exception) -> None:
        super().__init__(message)
        self.partial_result = partial_result
        self.__cause__ = cause


def _upsert_rolling_metric(
    db: Session,
    *,
    player_id: int,
    game_id: int,
    source_stat_id: int,
    metric_name: str,
    rolling_avg: float,
    rolling_stddev: float,
    z_score: float,
    generated_at: datetime,
) -> tuple[RollingMetric, bool]:
    rolling_metric = db.execute(
        select(RollingMetric).where(
            RollingMetric.player_id == player_id,
            RollingMetric.game_id == game_id,
            RollingMetric.metric_name == metric_name,
        )
    ).scalar_one_or_none()

    created = rolling_metric is None
    if rolling_metric is None:
        rolling_metric = RollingMetric(
            player_id=player_id,
            game_id=game_id,
            source_stat_id=source_stat_id,
            metric_name=metric_name,
            rolling_avg=rolling_avg,
            rolling_stddev=rolling_stddev,
            z_score=z_score,
            updated_at=generated_at,
        )
        db.add(rolling_metric)
    else:
        rolling_metric.source_stat_id = source_stat_id
        rolling_metric.rolling_avg = rolling_avg
        rolling_metric.rolling_stddev = rolling_stddev
        rolling_metric.z_score = z_score
        rolling_metric.updated_at = generated_at

    return rolling_metric, created


def _sync_rolling_metric_baseline_samples(
    db: Session,
    *,
    rolling_metric_id: int,
    baseline_stat_ids: list[int],
) -> None:
    db.execute(
        delete(RollingMetricBaselineSample).where(
            RollingMetricBaselineSample.rolling_metric_id == rolling_metric_id
        )
    )
    for sample_order, stat_id in enumerate(baseline_stat_ids):
        db.add(
            RollingMetricBaselineSample(
                rolling_metric_id=rolling_metric_id,
                player_game_stat_id=stat_id,
                sample_order=sample_order,
            )
        )


def _delete_stale_rolling_metrics(db: Session, *, player_id: int, valid_contexts: set[tuple[int, str]]) -> int:
    existing_contexts = db.execute(
        select(RollingMetric.game_id, RollingMetric.metric_name).where(RollingMetric.player_id == player_id)
    ).all()
    stale_contexts = [context for context in existing_contexts if context not in valid_contexts]
    if not stale_contexts:
        return 0

    deleted = 0
    for game_id, metric_name in stale_contexts:
        rolling_metric = db.execute(
            select(RollingMetric).where(
                RollingMetric.player_id == player_id,
                RollingMetric.game_id == game_id,
                RollingMetric.metric_name == metric_name,
            )
        ).scalar_one_or_none()
        if rolling_metric is None:
            continue
        db.execute(
            delete(RollingMetricBaselineSample).where(
                RollingMetricBaselineSample.rolling_metric_id == rolling_metric.id
            )
        )
        deleted += db.execute(
            delete(RollingMetric).where(
                RollingMetric.player_id == player_id,
                RollingMetric.game_id == game_id,
                RollingMetric.metric_name == metric_name,
            )
        ).rowcount or 0
    return deleted


def _delete_stale_signals(db: Session, *, player_id: int, valid_contexts: set[tuple[int, str]]) -> int:
    existing_contexts = db.execute(
        select(Signal.game_id, Signal.metric_name).where(Signal.player_id == player_id).distinct()
    ).all()
    stale_contexts = [context for context in existing_contexts if context not in valid_contexts]
    if not stale_contexts:
        return 0

    deleted = 0
    for game_id, metric_name in stale_contexts:
        deleted += db.execute(
            delete(Signal).where(
                Signal.player_id == player_id,
                Signal.game_id == game_id,
                Signal.metric_name == metric_name,
            )
        ).rowcount or 0
    return deleted


def _sync_signal_for_context(
    db: Session,
    *,
    player: Player,
    game_id: int,
    rolling_metric_id: int,
    source_stat_id: int,
    metric_name: str,
    signal_type: Optional[str],
    current_value: float,
    baseline_value: float,
    z_score: float,
    generated_at: datetime,
) -> tuple[int, int, int]:
    existing_signals = db.execute(
        select(Signal).where(
            Signal.player_id == player.id,
            Signal.game_id == game_id,
            Signal.metric_name == metric_name,
        )
    ).scalars().all()

    created = 0
    updated = 0
    deleted = 0

    for existing in existing_signals:
        if signal_type is None or existing.signal_type != signal_type:
            db.delete(existing)
            deleted += 1

    if signal_type is None:
        return created, updated, deleted

    explanation = build_explanation(player.name, metric_name, current_value, baseline_value, z_score, signal_type)
    current_signal = next((signal for signal in existing_signals if signal.signal_type == signal_type), None)

    if current_signal is None:
        db.add(
            Signal(
                player_id=player.id,
                game_id=game_id,
                rolling_metric_id=rolling_metric_id,
                source_stat_id=source_stat_id,
                team_id=player.team_id,
                league_id=player.league_id,
                signal_type=signal_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=z_score,
                explanation=explanation,
                created_at=generated_at,
            )
        )
        created += 1
        return created, updated, deleted

    current_signal.team_id = player.team_id
    current_signal.league_id = player.league_id
    current_signal.rolling_metric_id = rolling_metric_id
    current_signal.source_stat_id = source_stat_id
    current_signal.current_value = current_value
    current_signal.baseline_value = baseline_value
    current_signal.z_score = z_score
    current_signal.explanation = explanation
    current_signal.created_at = generated_at
    updated += 1
    return created, updated, deleted


def generate_signals(db: Session) -> SignalGenerationResult:
    result = SignalGenerationResult()
    try:
        players = db.execute(
            select(Player)
            .options(selectinload(Player.league))
            .order_by(Player.id)
        ).scalars().all()

        for player in players:
            stats = db.execute(
                select(PlayerGameStat)
                .join(Game, PlayerGameStat.game_id == Game.id)
                .where(PlayerGameStat.player_id == player.id)
                .order_by(Game.game_date, Game.id)
            ).scalars().all()

            metrics = METRICS_BY_LEAGUE[player.league.name]
            valid_contexts: set[tuple[int, str]] = set()

            for metric_name in metrics:
                for snapshot in build_metric_snapshots(metric_name, stats):
                    generated_at = datetime.utcnow()
                    valid_contexts.add((snapshot.game_id, metric_name))

                    rolling_metric, rolling_created = _upsert_rolling_metric(
                        db,
                        player_id=player.id,
                        game_id=snapshot.game_id,
                        source_stat_id=snapshot.source_stat_id,
                        metric_name=metric_name,
                        rolling_avg=snapshot.baseline_value,
                        rolling_stddev=snapshot.rolling_stddev,
                        z_score=snapshot.z_score,
                        generated_at=generated_at,
                    )
                    db.flush()
                    _sync_rolling_metric_baseline_samples(
                        db,
                        rolling_metric_id=rolling_metric.id,
                        baseline_stat_ids=snapshot.baseline_stat_ids,
                    )

                    signal_type = classify_signal(
                        snapshot.z_score,
                        snapshot.rolling_stddev,
                        metric_name,
                        snapshot.current_value,
                        snapshot.baseline_value,
                    )
                    created, updated, deleted = _sync_signal_for_context(
                        db,
                        player=player,
                        game_id=snapshot.game_id,
                        rolling_metric_id=rolling_metric.id,
                        source_stat_id=snapshot.source_stat_id,
                        metric_name=metric_name,
                        signal_type=signal_type,
                        current_value=snapshot.current_value,
                        baseline_value=snapshot.baseline_value,
                        z_score=snapshot.z_score,
                        generated_at=generated_at,
                    )

                    result = SignalGenerationResult(
                        created_signals=result.created_signals + created,
                        updated_signals=result.updated_signals + updated,
                        deleted_signals=result.deleted_signals + deleted,
                        created_rolling_metrics=result.created_rolling_metrics + int(rolling_created),
                        updated_rolling_metrics=result.updated_rolling_metrics + int(not rolling_created),
                        deleted_rolling_metrics=result.deleted_rolling_metrics,
                    )

            deleted_rolling_metrics = _delete_stale_rolling_metrics(db, player_id=player.id, valid_contexts=valid_contexts)
            deleted_signals = _delete_stale_signals(db, player_id=player.id, valid_contexts=valid_contexts)
            result = SignalGenerationResult(
                created_signals=result.created_signals,
                updated_signals=result.updated_signals,
                deleted_signals=result.deleted_signals + deleted_signals,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics + deleted_rolling_metrics,
            )

        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise SignalGenerationError(
            "Signal generation failed and transaction was rolled back.",
            partial_result=result,
            cause=exc,
        ) from exc
