from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domain.signals import BASELINE_WINDOW_SIZE, classification_reason
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.schemas.signal import (
    BaselineSampleRead,
    RollingMetricTraceRead,
    SignalTraceRead,
    SourceStatContextRead,
    WindowContextRead,
)
from app.services.signal_service import build_signal_read, effective_metric_to_snapshot


def _stat_value(stat: PlayerGameStat, metric_name: str) -> Optional[float]:
    value = getattr(stat, metric_name, None)
    return float(value) if value is not None else None


def _raw_stat_map(stat: PlayerGameStat) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in {
            "points": stat.points,
            "rebounds": stat.rebounds,
            "assists": stat.assists,
            "steals": stat.steals,
            "blocks": stat.blocks,
            "turnovers": stat.turnovers,
            "passing_yards": stat.passing_yards,
            "rushing_yards": stat.rushing_yards,
            "receiving_yards": stat.receiving_yards,
            "touchdowns": stat.touchdowns,
            "usage_rate": stat.usage_rate,
        }.items()
        if value is not None
    }


def _raw_team_stat_map(stat: TeamGameStat) -> dict[str, float]:
    return {
        key: float(value)
        for key, value in {
            "points": stat.points,
            "rebounds": stat.rebounds,
            "assists": stat.assists,
            "fg_pct": stat.fg_pct,
            "fg3_pct": stat.fg3_pct,
            "turnovers": stat.turnovers,
            "pace": stat.pace,
            "off_rating": stat.off_rating,
        }.items()
        if value is not None
    }


def _build_source_stat_context(
    stat: PlayerGameStat,
    *,
    game_date,
    metric_name: str,
    current_value: float,
) -> SourceStatContextRead:
    return SourceStatContextRead(
        stat_id=stat.id,
        game_id=stat.game_id,
        game_date=game_date,
        metric_name=metric_name,
        current_value=current_value,
        raw_stats=_raw_stat_map(stat),
        source_system=stat.source_system,
        source_game_id=stat.source_game_id,
        source_player_id=stat.source_player_id,
        raw_snapshot_path=stat.raw_snapshot_path,
        raw_payload_path=stat.raw_payload_path,
        raw_record_index=stat.raw_record_index,
    )


def _build_team_source_stat_context(
    stat: TeamGameStat,
    *,
    game_date,
    metric_name: str,
    current_value: float,
) -> SourceStatContextRead:
    return SourceStatContextRead(
        stat_id=stat.id,
        game_id=stat.game_id,
        game_date=game_date,
        metric_name=metric_name,
        current_value=current_value,
        raw_stats=_raw_team_stat_map(stat),
        source_system=stat.source_system,
        source_game_id=stat.source_game_id,
        source_team_id=stat.source_team_id,
        raw_snapshot_path=stat.raw_snapshot_path,
        raw_payload_path=stat.raw_traditional_payload_path,
        raw_advanced_payload_path=stat.raw_advanced_payload_path,
        raw_record_index=stat.raw_record_index,
    )


def _build_baseline_sample(
    stat: PlayerGameStat,
    *,
    game_date,
    metric_name: str,
) -> Optional[BaselineSampleRead]:
    value = _stat_value(stat, metric_name)
    if value is None:
        return None
    return BaselineSampleRead(
        stat_id=stat.id,
        game_id=stat.game_id,
        game_date=game_date,
        value=value,
        source_system=stat.source_system,
        source_game_id=stat.source_game_id,
        source_player_id=stat.source_player_id,
        raw_snapshot_path=stat.raw_snapshot_path,
        raw_payload_path=stat.raw_payload_path,
        raw_record_index=stat.raw_record_index,
    )


def _build_team_baseline_sample(
    stat: TeamGameStat,
    *,
    game_date,
    metric_name: str,
) -> Optional[BaselineSampleRead]:
    value = getattr(stat, metric_name, None)
    if value is None:
        return None
    return BaselineSampleRead(
        stat_id=stat.id,
        game_id=stat.game_id,
        game_date=game_date,
        value=float(value),
        source_system=stat.source_system,
        source_game_id=stat.source_game_id,
        source_team_id=stat.source_team_id,
        raw_snapshot_path=stat.raw_snapshot_path,
        raw_payload_path=stat.raw_traditional_payload_path,
        raw_advanced_payload_path=stat.raw_advanced_payload_path,
        raw_record_index=stat.raw_record_index,
    )


def _fallback_source_and_baseline(
    db: Session,
    *,
    signal: Signal,
) -> tuple[Optional[PlayerGameStat], list[BaselineSampleRead]]:
    stat_rows = db.execute(
        select(PlayerGameStat, Game.game_date)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .where(PlayerGameStat.player_id == signal.player_id)
        .order_by(Game.game_date, Game.id)
    ).all()

    current_index = next((index for index, (stat, _) in enumerate(stat_rows) if stat.game_id == signal.game_id), None)
    if current_index is None:
        return None, []

    current_stat, _ = stat_rows[current_index]
    observations = [
        (stat, game_date)
        for stat, game_date in stat_rows
        if _stat_value(stat, signal.metric_name) is not None
    ]
    observation_index = next((index for index, (stat, _) in enumerate(observations) if stat.game_id == signal.game_id), None)
    prior_values = observations[:observation_index] if observation_index is not None else []
    baseline_rows = prior_values[-BASELINE_WINDOW_SIZE:] or prior_values

    baseline_samples = []
    for stat, game_date in baseline_rows:
        sample = _build_baseline_sample(stat, game_date=game_date, metric_name=signal.metric_name)
        if sample is not None:
            baseline_samples.append(sample)
    return current_stat, baseline_samples


def _fallback_team_source_and_baseline(
    db: Session,
    *,
    signal: Signal,
) -> tuple[Optional[TeamGameStat], list[BaselineSampleRead]]:
    stat_rows = db.execute(
        select(TeamGameStat, Game.game_date)
        .join(Game, TeamGameStat.game_id == Game.id)
        .where(TeamGameStat.team_id == signal.team_id)
        .order_by(Game.game_date, Game.id)
    ).all()

    current_index = next((index for index, (stat, _) in enumerate(stat_rows) if stat.game_id == signal.game_id), None)
    if current_index is None:
        return None, []

    current_stat, _ = stat_rows[current_index]
    observations = [
        (stat, game_date)
        for stat, game_date in stat_rows
        if getattr(stat, signal.metric_name, None) is not None
    ]
    observation_index = next((index for index, (stat, _) in enumerate(observations) if stat.game_id == signal.game_id), None)
    prior_values = observations[:observation_index] if observation_index is not None else []
    baseline_rows = prior_values[-BASELINE_WINDOW_SIZE:] or prior_values

    baseline_samples = []
    for stat, game_date in baseline_rows:
        sample = _build_team_baseline_sample(stat, game_date=game_date, metric_name=signal.metric_name)
        if sample is not None:
            baseline_samples.append(sample)
    return current_stat, baseline_samples


def inspect_signal(db: Session, signal_id: int) -> Optional[SignalTraceRead]:
    row = db.execute(
        select(Signal, Player.name, Team.name, League.name, Game.game_date, RollingMetric)
        .outerjoin(Player, Signal.player_id == Player.id)
        .join(Team, Signal.team_id == Team.id)
        .join(League, Signal.league_id == League.id)
        .join(Game, Signal.game_id == Game.id)
        .outerjoin(
            RollingMetric,
            and_(
                RollingMetric.id == Signal.rolling_metric_id,
            ),
        )
        .where(Signal.id == signal_id)
    ).one_or_none()

    if row is None:
        return None

    signal, player_name, team_name, league_name, event_date, rolling_metric = row

    if rolling_metric is None:
        if signal.player_id is not None:
            rolling_metric = db.execute(
                select(RollingMetric).where(
                    RollingMetric.player_id == signal.player_id,
                    RollingMetric.game_id == signal.game_id,
                    RollingMetric.metric_name == signal.metric_name,
                )
            ).scalar_one_or_none()

    source_stat = None
    baseline_samples: list[BaselineSampleRead] = []

    if signal.subject_type == "team" and signal.source_team_stat_id is not None:
        source_row = db.execute(
            select(TeamGameStat, Game.game_date)
            .join(Game, TeamGameStat.game_id == Game.id)
            .where(TeamGameStat.id == signal.source_team_stat_id)
        ).one_or_none()
        if source_row is not None:
            stat, game_date = source_row
            source_stat = _build_team_source_stat_context(
                stat,
                game_date=game_date,
                metric_name=signal.metric_name,
                current_value=float(getattr(stat, signal.metric_name) or signal.current_value),
            )
    elif signal.source_stat_id is not None:
        source_row = db.execute(
            select(PlayerGameStat, Game.game_date)
            .join(Game, PlayerGameStat.game_id == Game.id)
            .where(PlayerGameStat.id == signal.source_stat_id)
        ).one_or_none()
        if source_row is not None:
            stat, game_date = source_row
            source_stat = _build_source_stat_context(
                stat,
                game_date=game_date,
                metric_name=signal.metric_name,
                current_value=_stat_value(stat, signal.metric_name) or signal.current_value,
            )

    if signal.subject_type == "team":
        fallback_stat, fallback_samples = _fallback_team_source_and_baseline(db, signal=signal)
        if fallback_stat is None:
            return None
        if source_stat is None:
            fallback_game_date = db.execute(select(Game.game_date).where(Game.id == fallback_stat.game_id)).scalar_one()
            source_stat = _build_team_source_stat_context(
                fallback_stat,
                game_date=fallback_game_date,
                metric_name=signal.metric_name,
                current_value=float(getattr(fallback_stat, signal.metric_name) or signal.current_value),
            )
        baseline_samples = fallback_samples
    elif rolling_metric is not None:
        baseline_rows = db.execute(
            select(PlayerGameStat, Game.game_date)
            .join(
                RollingMetricBaselineSample,
                RollingMetricBaselineSample.player_game_stat_id == PlayerGameStat.id,
            )
            .join(Game, PlayerGameStat.game_id == Game.id)
            .where(RollingMetricBaselineSample.rolling_metric_id == rolling_metric.id)
            .order_by(RollingMetricBaselineSample.sample_order)
        ).all()
        for stat, game_date in baseline_rows:
            sample = _build_baseline_sample(stat, game_date=game_date, metric_name=signal.metric_name)
            if sample is not None:
                baseline_samples.append(sample)

    if signal.subject_type != "team" and (source_stat is None or not baseline_samples):
        fallback_stat, fallback_samples = _fallback_source_and_baseline(db, signal=signal)
        if fallback_stat is None:
            return None
        if source_stat is None:
            fallback_game_date = db.execute(select(Game.game_date).where(Game.id == fallback_stat.game_id)).scalar_one()
            source_stat = _build_source_stat_context(
                fallback_stat,
                game_date=fallback_game_date,
                metric_name=signal.metric_name,
                current_value=_stat_value(fallback_stat, signal.metric_name) or signal.current_value,
            )
        if not baseline_samples:
            baseline_samples = fallback_samples

    signal_read = build_signal_read(
        signal,
        player_name,
        team_name,
        league_name,
        event_date,
        rolling_metric,
    )
    snapshot = effective_metric_to_snapshot(signal, rolling_metric)
    signal_read.classification_reason = classification_reason(signal.signal_type, snapshot, signal.metric_name)

    rolling_metric_read = RollingMetricTraceRead(
        id=rolling_metric.id if rolling_metric is not None else None,
        player_id=signal.player_id,
        game_id=signal.game_id,
        metric_name=signal.metric_name,
        source_stat_id=rolling_metric.source_stat_id if rolling_metric is not None else signal.source_stat_id,
        rolling_avg=rolling_metric.rolling_avg if rolling_metric is not None else signal.baseline_value,
        rolling_stddev=rolling_metric.rolling_stddev if rolling_metric is not None else 0.0,
        z_score=rolling_metric.z_score if rolling_metric is not None else signal.z_score,
        short_window=WindowContextRead(
            sample_size=len(rolling_metric.short_values) if rolling_metric and rolling_metric.short_values else len(snapshot.short_window.values),
            values=[float(value) for value in ((rolling_metric.short_values if rolling_metric and rolling_metric.short_values else snapshot.short_window.values))],
            rolling_avg=rolling_metric.short_rolling_avg if rolling_metric and rolling_metric.short_rolling_avg is not None else snapshot.short_window.rolling_avg,
            rolling_stddev=rolling_metric.short_rolling_stddev if rolling_metric and rolling_metric.short_rolling_stddev is not None else snapshot.short_window.rolling_stddev,
            z_score=rolling_metric.short_z_score if rolling_metric and rolling_metric.short_z_score is not None else snapshot.short_window.z_score,
        ),
        medium_window=WindowContextRead(
            sample_size=len(rolling_metric.medium_values) if rolling_metric and rolling_metric.medium_values else len(snapshot.medium_window.values),
            values=[float(value) for value in ((rolling_metric.medium_values if rolling_metric and rolling_metric.medium_values else snapshot.medium_window.values))],
            rolling_avg=rolling_metric.medium_rolling_avg if rolling_metric and rolling_metric.medium_rolling_avg is not None else snapshot.medium_window.rolling_avg,
            rolling_stddev=rolling_metric.medium_rolling_stddev if rolling_metric and rolling_metric.medium_rolling_stddev is not None else snapshot.medium_window.rolling_stddev,
            z_score=rolling_metric.medium_z_score if rolling_metric and rolling_metric.medium_z_score is not None else snapshot.medium_window.z_score,
        ),
        season_window=WindowContextRead(
            sample_size=len(rolling_metric.season_values) if rolling_metric and rolling_metric.season_values else len(snapshot.season_window.values),
            values=[float(value) for value in ((rolling_metric.season_values if rolling_metric and rolling_metric.season_values else snapshot.season_window.values))],
            rolling_avg=rolling_metric.season_rolling_avg if rolling_metric and rolling_metric.season_rolling_avg is not None else snapshot.season_window.rolling_avg,
            rolling_stddev=rolling_metric.season_rolling_stddev if rolling_metric and rolling_metric.season_rolling_stddev is not None else snapshot.season_window.rolling_stddev,
            z_score=rolling_metric.season_z_score if rolling_metric and rolling_metric.season_z_score is not None else snapshot.season_window.z_score,
        ),
        ewma=rolling_metric.ewma if rolling_metric is not None else snapshot.ewma,
        recent_delta=rolling_metric.recent_delta if rolling_metric is not None else snapshot.recent_delta,
        trend_slope=rolling_metric.trend_slope if rolling_metric is not None else snapshot.trend_slope,
        volatility_index=rolling_metric.volatility_index if rolling_metric is not None else snapshot.volatility_index,
        volatility_delta=rolling_metric.volatility_delta if rolling_metric is not None else snapshot.volatility_delta,
        opponent_average_allowed=rolling_metric.opponent_average_allowed if rolling_metric is not None else snapshot.opponent_average_allowed,
        opponent_rank=rolling_metric.opponent_rank if rolling_metric is not None else snapshot.opponent_rank,
        pace_proxy=rolling_metric.pace_proxy if rolling_metric is not None else snapshot.pace_proxy,
        usage_shift=rolling_metric.usage_shift if rolling_metric is not None else snapshot.usage_shift,
        high_volatility=rolling_metric.high_volatility if rolling_metric is not None else snapshot.high_volatility,
    )

    return SignalTraceRead(
        signal=signal_read,
        rolling_metric=rolling_metric_read,
        source_stat=source_stat,
        baseline_samples=baseline_samples,
    )
