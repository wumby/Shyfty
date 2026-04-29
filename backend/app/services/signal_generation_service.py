from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.signals import (
    METRICS_BY_LEAGUE,
    TEAM_METRICS_BY_LEAGUE,
    build_explanation,
    build_metric_snapshots,
    build_narrative_summary,
    classify_signal,
    score_signal,
)
from app.models.game import Game
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat

MAX_SIGNALS_PER_PLAYER_GAME = 3


@dataclass(frozen=True)
class SignalGenerationResult:
    created_signals: int = 0
    updated_signals: int = 0
    deleted_signals: int = 0
    created_rolling_metrics: int = 0
    updated_rolling_metrics: int = 0
    deleted_rolling_metrics: int = 0


@dataclass(frozen=True)
class SignalGenerationContext:
    game_dates: dict[int, object]
    game_pace_proxy: dict[int, float]
    opponent_average_allowed: dict[tuple[int, str], float]
    opponent_rank: dict[tuple[int, str], int]


@dataclass(frozen=True)
class PlayerSignalCandidate:
    player: Player
    game_id: int
    rolling_metric_id: int
    source_stat_id: int
    metric_name: str
    signal_type: str
    current_value: float
    baseline_value: float
    z_score: float
    signal_score: float
    score_explanation: str
    explanation: str
    narrative_summary: Optional[str]
    generated_at: datetime


class SignalGenerationError(RuntimeError):
    def __init__(self, message: str, *, partial_result: SignalGenerationResult, cause: Exception) -> None:
        super().__init__(message)
        self.partial_result = partial_result
        self.__cause__ = cause


def build_signal_generation_context(db: Session) -> SignalGenerationContext:
    game_rows = db.execute(select(Game.id, Game.game_date, Game.home_team_id, Game.away_team_id)).all()
    game_meta = {
        game_id: {
            "game_date": game_date,
            "home_team_id": home_team_id,
            "away_team_id": away_team_id,
        }
        for game_id, game_date, home_team_id, away_team_id in game_rows
    }

    metric_names = sorted({metric for metrics in METRICS_BY_LEAGUE.values() for metric in metrics})
    stat_rows = db.execute(
        select(PlayerGameStat, Player.team_id)
        .join(Player, PlayerGameStat.player_id == Player.id)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .order_by(Game.game_date, Game.id, PlayerGameStat.id)
    ).all()

    game_pace_parts: dict[int, list[float]] = {}
    for stat, _ in stat_rows:
        game_pace_parts.setdefault(stat.game_id, []).append(
            float(stat.points or 0) + float(stat.rebounds or 0) + float(stat.assists or 0)
        )
    game_pace_proxy = {game_id: round(sum(parts), 2) for game_id, parts in game_pace_parts.items()}

    team_allowed_history: dict[str, dict[int, list[float]]] = {metric_name: {} for metric_name in metric_names}
    opponent_average_allowed: dict[tuple[int, str], float] = {}
    opponent_rank: dict[tuple[int, str], int] = {}

    for stat, team_id in stat_rows:
        game = game_meta.get(stat.game_id)
        if game is None:
            continue
        opponent_team_id = game["away_team_id"] if team_id == game["home_team_id"] else game["home_team_id"]

        for metric_name in metric_names:
            value = getattr(stat, metric_name, None)
            if value is None:
                continue

            history = team_allowed_history.setdefault(metric_name, {})
            prior_values = history.get(opponent_team_id, [])
            if prior_values:
                opponent_average_allowed[(stat.id, metric_name)] = round(mean(prior_values), 4)

            ranked = [(team_key, mean(values)) for team_key, values in history.items() if values]
            ranked.sort(key=lambda item: item[1])
            for index, (team_key, _) in enumerate(ranked, start=1):
                if team_key == opponent_team_id:
                    opponent_rank[(stat.id, metric_name)] = index
                    break

            history.setdefault(opponent_team_id, []).append(float(value))

    return SignalGenerationContext(
        game_dates={game_id: meta["game_date"] for game_id, meta in game_meta.items()},
        game_pace_proxy=game_pace_proxy,
        opponent_average_allowed=opponent_average_allowed,
        opponent_rank=opponent_rank,
    )


def _upsert_rolling_metric(
    db: Session,
    *,
    player_id: int,
    game_id: int,
    source_stat_id: int,
    metric_name: str,
    snapshot,
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
            rolling_avg=snapshot.baseline_value,
            rolling_stddev=snapshot.rolling_stddev,
            z_score=snapshot.z_score,
            updated_at=generated_at,
        )
        db.add(rolling_metric)

    rolling_metric.source_stat_id = source_stat_id
    rolling_metric.rolling_avg = snapshot.baseline_value
    rolling_metric.rolling_stddev = snapshot.rolling_stddev
    rolling_metric.z_score = snapshot.z_score
    rolling_metric.short_window_size = snapshot.short_window.sample_size
    rolling_metric.medium_window_size = snapshot.medium_window.sample_size
    rolling_metric.season_window_size = snapshot.season_window.sample_size
    rolling_metric.short_values = snapshot.short_window.values
    rolling_metric.medium_values = snapshot.medium_window.values
    rolling_metric.season_values = snapshot.season_window.values
    rolling_metric.short_rolling_avg = snapshot.short_window.rolling_avg
    rolling_metric.short_rolling_stddev = snapshot.short_window.rolling_stddev
    rolling_metric.short_z_score = snapshot.short_window.z_score
    rolling_metric.medium_rolling_avg = snapshot.medium_window.rolling_avg
    rolling_metric.medium_rolling_stddev = snapshot.medium_window.rolling_stddev
    rolling_metric.medium_z_score = snapshot.medium_window.z_score
    rolling_metric.season_rolling_avg = snapshot.season_window.rolling_avg
    rolling_metric.season_rolling_stddev = snapshot.season_window.rolling_stddev
    rolling_metric.season_z_score = snapshot.season_window.z_score
    rolling_metric.ewma = snapshot.ewma
    rolling_metric.recent_delta = snapshot.recent_delta
    rolling_metric.trend_slope = snapshot.trend_slope
    rolling_metric.volatility_index = snapshot.volatility_index
    rolling_metric.volatility_delta = snapshot.volatility_delta
    rolling_metric.opponent_average_allowed = snapshot.opponent_average_allowed
    rolling_metric.opponent_rank = snapshot.opponent_rank
    rolling_metric.pace_proxy = snapshot.pace_proxy
    rolling_metric.usage_shift = snapshot.usage_shift
    rolling_metric.high_volatility = snapshot.high_volatility
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


def _delete_stale_team_signals(db: Session, *, team_id: int, valid_contexts: set[tuple[int, str]]) -> int:
    existing_contexts = db.execute(
        select(Signal.game_id, Signal.metric_name).where(
            Signal.team_id == team_id,
            Signal.subject_type == "team",
        )
    ).all()
    stale_contexts = [context for context in existing_contexts if context not in valid_contexts]
    if not stale_contexts:
        return 0

    deleted = 0
    for game_id, metric_name in stale_contexts:
        deleted += db.execute(
            delete(Signal).where(
                Signal.team_id == team_id,
                Signal.subject_type == "team",
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
    signal_score: float,
    score_explanation: str,
    explanation: str,
    narrative_summary: Optional[str],
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

    current_signal = next((signal for signal in existing_signals if signal.signal_type == signal_type), None)
    if current_signal is None:
        db.add(
            Signal(
                player_id=player.id,
                game_id=game_id,
                rolling_metric_id=rolling_metric_id,
                source_stat_id=source_stat_id,
                source_team_stat_id=None,
                team_id=player.team_id,
                league_id=player.league_id,
                subject_type="player",
                signal_type=signal_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=z_score,
                signal_score=signal_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative_summary,
                created_at=generated_at,
            )
        )
        created += 1
        return created, updated, deleted

    current_signal.team_id = player.team_id
    current_signal.league_id = player.league_id
    current_signal.subject_type = "player"
    current_signal.rolling_metric_id = rolling_metric_id
    current_signal.source_stat_id = source_stat_id
    current_signal.source_team_stat_id = None
    current_signal.current_value = current_value
    current_signal.baseline_value = baseline_value
    current_signal.z_score = z_score
    current_signal.signal_score = signal_score
    current_signal.score_explanation = score_explanation
    current_signal.explanation = explanation
    current_signal.narrative_summary = narrative_summary
    updated += 1
    return created, updated, deleted


def _sync_player_signal_candidates(
    db: Session,
    candidates: list[PlayerSignalCandidate],
) -> tuple[int, int, int]:
    by_game: dict[int, list[PlayerSignalCandidate]] = {}
    for candidate in candidates:
        by_game.setdefault(candidate.game_id, []).append(candidate)

    created = 0
    updated = 0
    deleted = 0
    for game_candidates in by_game.values():
        ranked = sorted(game_candidates, key=lambda candidate: candidate.signal_score, reverse=True)
        kept_keys = {(candidate.game_id, candidate.metric_name) for candidate in ranked[:MAX_SIGNALS_PER_PLAYER_GAME]}
        for candidate in ranked:
            signal_type = (
                candidate.signal_type
                if (candidate.game_id, candidate.metric_name) in kept_keys
                else None
            )
            candidate_created, candidate_updated, candidate_deleted = _sync_signal_for_context(
                db,
                player=candidate.player,
                game_id=candidate.game_id,
                rolling_metric_id=candidate.rolling_metric_id,
                source_stat_id=candidate.source_stat_id,
                metric_name=candidate.metric_name,
                signal_type=signal_type,
                current_value=candidate.current_value,
                baseline_value=candidate.baseline_value,
                z_score=candidate.z_score,
                signal_score=candidate.signal_score if signal_type is not None else 0.0,
                score_explanation=candidate.score_explanation if signal_type is not None else "",
                explanation=candidate.explanation,
                narrative_summary=candidate.narrative_summary if signal_type is not None else None,
                generated_at=candidate.generated_at,
            )
            created += candidate_created
            updated += candidate_updated
            deleted += candidate_deleted
    return created, updated, deleted


def _sync_team_signal_for_context(
    db: Session,
    *,
    team: Team,
    game_id: int,
    source_team_stat_id: int,
    metric_name: str,
    signal_type: Optional[str],
    current_value: float,
    baseline_value: float,
    z_score: float,
    signal_score: float,
    score_explanation: str,
    explanation: str,
    narrative_summary: Optional[str],
    generated_at: datetime,
) -> tuple[int, int, int]:
    existing_signals = db.execute(
        select(Signal).where(
            Signal.team_id == team.id,
            Signal.subject_type == "team",
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

    current_signal = next(
        (
            signal
            for signal in existing_signals
            if signal.metric_name == metric_name and signal.signal_type == signal_type
        ),
        None,
    )
    if current_signal is None:
        db.add(
            Signal(
                player_id=None,
                game_id=game_id,
                rolling_metric_id=None,
                source_stat_id=None,
                source_team_stat_id=source_team_stat_id,
                team_id=team.id,
                league_id=team.league_id,
                subject_type="team",
                signal_type=signal_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=z_score,
                signal_score=signal_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative_summary,
                created_at=generated_at,
            )
        )
        created += 1
        return created, updated, deleted

    current_signal.player_id = None
    current_signal.rolling_metric_id = None
    current_signal.source_stat_id = None
    current_signal.source_team_stat_id = source_team_stat_id
    current_signal.team_id = team.id
    current_signal.league_id = team.league_id
    current_signal.subject_type = "team"
    current_signal.current_value = current_value
    current_signal.baseline_value = baseline_value
    current_signal.z_score = z_score
    current_signal.signal_score = signal_score
    current_signal.score_explanation = score_explanation
    current_signal.explanation = explanation
    current_signal.narrative_summary = narrative_summary
    updated += 1
    return created, updated, deleted


def _generate_team_signals(
    db: Session,
    *,
    result: SignalGenerationResult,
    team_ids: Optional[list[int]] = None,
) -> SignalGenerationResult:
    teams_query = select(Team).options(selectinload(Team.league))
    if team_ids:
        teams_query = teams_query.where(Team.id.in_(team_ids))
    teams = db.execute(teams_query.order_by(Team.id)).scalars().all()

    for team in teams:
        metrics = TEAM_METRICS_BY_LEAGUE.get(team.league.name if team.league else "", [])
        if not metrics:
            continue

        team_stats = db.execute(
            select(TeamGameStat)
            .join(Game, TeamGameStat.game_id == Game.id)
            .where(TeamGameStat.team_id == team.id)
            .order_by(Game.game_date, Game.id)
        ).scalars().all()
        metric_stats = {
            metric_name: [stat for stat in team_stats if getattr(stat, metric_name, None) is not None]
            for metric_name in metrics
        }
        candidates_by_game: dict[int, tuple[str, object, float, float, float]] = {}

        for metric_name in metrics:
            snapshots = build_metric_snapshots(
                metric_name,
                metric_stats.get(metric_name, []),
            )
            for snapshot in snapshots:
                severity = classify_signal(snapshot, metric_name)
                if severity is None:
                    continue
                stat = next((team_stat for team_stat in team_stats if team_stat.id == snapshot.source_stat_id), None)
                if stat is None:
                    continue
                candidate_strength = abs(snapshot.z_score) + abs(snapshot.current_value - snapshot.baseline_value)
                current_best = candidates_by_game.get(snapshot.game_id)
                if current_best is None or candidate_strength > current_best[4]:
                    candidates_by_game[snapshot.game_id] = (
                        metric_name,
                        snapshot,
                        snapshot.current_value,
                        snapshot.baseline_value,
                        candidate_strength,
                    )

        valid_contexts: set[tuple[int, str]] = set()
        for game_id, (metric_name, snapshot, current_value, baseline_value, _candidate_strength) in candidates_by_game.items():
            stat = next((team_stat for team_stat in team_stats if team_stat.id == snapshot.source_stat_id), None)
            if stat is None:
                continue
            signal_type = classify_signal(snapshot, metric_name)
            if signal_type is None:
                continue
            generated_at = datetime.utcnow()
            valid_contexts.add((game_id, metric_name))
            explanation = build_explanation(
                team.name,
                metric_name,
                current_value,
                baseline_value,
                snapshot.z_score,
                signal_type,
                snapshot=snapshot,
            )
            narrative = build_narrative_summary(signal_type, snapshot, metric_name)
            signal_score, score_explanation = score_signal(
                snapshot,
                signal_type=signal_type,
                metric_name=metric_name,
                event_date=snapshot.event_date,
                latest_event_date=None,
            )
            created, updated, deleted = _sync_team_signal_for_context(
                db,
                team=team,
                game_id=game_id,
                source_team_stat_id=stat.id,
                metric_name=metric_name,
                signal_type=signal_type,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=snapshot.z_score,
                signal_score=signal_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative,
                generated_at=generated_at,
            )
            result = SignalGenerationResult(
                created_signals=result.created_signals + created,
                updated_signals=result.updated_signals + updated,
                deleted_signals=result.deleted_signals + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics,
            )

        deleted_signals = _delete_stale_team_signals(db, team_id=team.id, valid_contexts=valid_contexts)
        result = SignalGenerationResult(
            created_signals=result.created_signals,
            updated_signals=result.updated_signals,
            deleted_signals=result.deleted_signals + deleted_signals,
            created_rolling_metrics=result.created_rolling_metrics,
            updated_rolling_metrics=result.updated_rolling_metrics,
            deleted_rolling_metrics=result.deleted_rolling_metrics,
        )

    return result


def generate_signals_for_players(
    db: Session,
    player_ids: list[int],
    team_ids: Optional[list[int]] = None,
) -> SignalGenerationResult:
    """Recompute signals for a specific set of players.

    Used by the incremental ingest path after new game data is loaded for known players.
    Builds the full signal generation context (opponent history, pace) globally so that
    per-player metrics remain accurate relative to the whole league, then restricts
    the computation loop to the provided player IDs.

    Future Kafka consumer plug-in point:
        After a stream consumer processes a game event and loads it via
        load_nba_games_incremental(), it calls this function with the IDs of the
        players whose stats just changed. Signals are updated in near-real-time
        without reprocessing the entire player roster.

    Args:
        player_ids: internal DB player IDs whose signals should be regenerated.
    """
    if not player_ids and not team_ids:
        return SignalGenerationResult()

    result = SignalGenerationResult()
    try:
        context = build_signal_generation_context(db)
        latest_event_date = max(context.game_dates.values()) if context.game_dates else None

        players = []
        if player_ids:
            players = db.execute(
                select(Player)
                .options(selectinload(Player.league))
                .where(Player.id.in_(player_ids))
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
            metric_stats = {
                metric_name: [stat for stat in stats if getattr(stat, metric_name, None) is not None]
                for metric_name in metrics
            }
            usage_snapshots = (
                {
                    snapshot.game_id: snapshot
                    for snapshot in build_metric_snapshots(
                        "usage_rate",
                        metric_stats.get("usage_rate", []),
                        game_dates_by_game_id=context.game_dates,
                    )
                }
                if "usage_rate" in metrics
                else {}
            )
            minutes_snapshots_by_game_id = (
                {
                    snapshot.game_id: snapshot
                    for snapshot in build_metric_snapshots(
                        "minutes_played",
                        metric_stats.get("minutes_played", []),
                        game_dates_by_game_id=context.game_dates,
                    )
                }
                if "minutes_played" in metrics
                else {}
            )
            signal_candidates: list[PlayerSignalCandidate] = []

            for metric_name in metrics:
                snapshots = build_metric_snapshots(
                    metric_name,
                    metric_stats.get(metric_name, []),
                    game_dates_by_game_id=context.game_dates,
                )
                for snapshot in snapshots:
                    generated_at = datetime.utcnow()
                    valid_contexts.add((snapshot.game_id, metric_name))
                    usage_snapshot = usage_snapshots.get(snapshot.game_id)
                    minutes_snapshot = minutes_snapshots_by_game_id.get(snapshot.game_id)
                    contextual_snapshot = snapshot.with_context(
                        opponent_average_allowed=context.opponent_average_allowed.get((snapshot.source_stat_id, metric_name)),
                        opponent_rank=context.opponent_rank.get((snapshot.source_stat_id, metric_name)),
                        pace_proxy=context.game_pace_proxy.get(snapshot.game_id),
                        usage_shift=(
                            snapshot.current_value - snapshot.medium_window.rolling_avg
                            if metric_name == "usage_rate"
                            else (usage_snapshot.current_value - usage_snapshot.medium_window.rolling_avg if usage_snapshot else None)
                        ),
                        minutes_current=minutes_snapshot.current_value if minutes_snapshot else None,
                        minutes_baseline=minutes_snapshot.baseline_value if minutes_snapshot else None,
                    )

                    rolling_metric, rolling_created = _upsert_rolling_metric(
                        db,
                        player_id=player.id,
                        game_id=contextual_snapshot.game_id,
                        source_stat_id=contextual_snapshot.source_stat_id,
                        metric_name=metric_name,
                        snapshot=contextual_snapshot,
                        generated_at=generated_at,
                    )
                    db.flush()
                    _sync_rolling_metric_baseline_samples(
                        db,
                        rolling_metric_id=rolling_metric.id,
                        baseline_stat_ids=contextual_snapshot.baseline_stat_ids,
                    )

                    signal_type = classify_signal(contextual_snapshot, metric_name)
                    signal_score = 0.0
                    score_explanation = ""
                    if signal_type is not None:
                        signal_score, score_explanation = score_signal(
                            contextual_snapshot,
                            signal_type=signal_type,
                            metric_name=metric_name,
                            event_date=contextual_snapshot.event_date,
                            latest_event_date=latest_event_date,
                        )

                    explanation = build_explanation(
                        player.name,
                        metric_name,
                        contextual_snapshot.current_value,
                        contextual_snapshot.baseline_value,
                        contextual_snapshot.z_score,
                        signal_type,
                        snapshot=contextual_snapshot,
                    )

                    narrative = (
                        build_narrative_summary(signal_type, contextual_snapshot, metric_name)
                        if signal_type is not None
                        else None
                    )

                    if signal_type is None:
                        created, updated, deleted = _sync_signal_for_context(
                            db,
                            player=player,
                            game_id=contextual_snapshot.game_id,
                            rolling_metric_id=rolling_metric.id,
                            source_stat_id=contextual_snapshot.source_stat_id,
                            metric_name=metric_name,
                            signal_type=None,
                            current_value=contextual_snapshot.current_value,
                            baseline_value=contextual_snapshot.baseline_value,
                            z_score=contextual_snapshot.z_score,
                            signal_score=0.0,
                            score_explanation="",
                            explanation=explanation,
                            narrative_summary=None,
                            generated_at=generated_at,
                        )
                    else:
                        signal_candidates.append(
                            PlayerSignalCandidate(
                                player=player,
                                game_id=contextual_snapshot.game_id,
                                rolling_metric_id=rolling_metric.id,
                                source_stat_id=contextual_snapshot.source_stat_id,
                                metric_name=metric_name,
                                signal_type=signal_type,
                                current_value=contextual_snapshot.current_value,
                                baseline_value=contextual_snapshot.baseline_value,
                                z_score=contextual_snapshot.z_score,
                                signal_score=signal_score,
                                score_explanation=score_explanation,
                                explanation=explanation,
                                narrative_summary=narrative,
                                generated_at=generated_at,
                            )
                        )
                        created = updated = deleted = 0

                    result = SignalGenerationResult(
                        created_signals=result.created_signals + created,
                        updated_signals=result.updated_signals + updated,
                        deleted_signals=result.deleted_signals + deleted,
                        created_rolling_metrics=result.created_rolling_metrics + int(rolling_created),
                        updated_rolling_metrics=result.updated_rolling_metrics + int(not rolling_created),
                        deleted_rolling_metrics=result.deleted_rolling_metrics,
                    )

            created, updated, deleted = _sync_player_signal_candidates(db, signal_candidates)
            result = SignalGenerationResult(
                created_signals=result.created_signals + created,
                updated_signals=result.updated_signals + updated,
                deleted_signals=result.deleted_signals + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
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

        result = _generate_team_signals(db, result=result, team_ids=team_ids)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise SignalGenerationError(
            "Incremental signal generation failed and transaction was rolled back.",
            partial_result=result,
            cause=exc,
        ) from exc


def generate_signals(db: Session) -> SignalGenerationResult:
    result = SignalGenerationResult()
    try:
        context = build_signal_generation_context(db)
        latest_event_date = max(context.game_dates.values()) if context.game_dates else None

        players = db.execute(
            select(Player).options(selectinload(Player.league)).order_by(Player.id)
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
            metric_stats = {
                metric_name: [stat for stat in stats if getattr(stat, metric_name, None) is not None]
                for metric_name in metrics
            }
            usage_snapshots = {
                snapshot.game_id: snapshot
                for snapshot in build_metric_snapshots(
                    "usage_rate",
                    metric_stats.get("usage_rate", []),
                    game_dates_by_game_id=context.game_dates,
                )
            } if "usage_rate" in metrics else {}
            minutes_snapshots_by_game_id = {
                snapshot.game_id: snapshot
                for snapshot in build_metric_snapshots(
                    "minutes_played",
                    metric_stats.get("minutes_played", []),
                    game_dates_by_game_id=context.game_dates,
                )
            } if "minutes_played" in metrics else {}
            signal_candidates: list[PlayerSignalCandidate] = []

            for metric_name in metrics:
                snapshots = build_metric_snapshots(
                    metric_name,
                    metric_stats.get(metric_name, []),
                    game_dates_by_game_id=context.game_dates,
                )
                for snapshot in snapshots:
                    generated_at = datetime.utcnow()
                    valid_contexts.add((snapshot.game_id, metric_name))
                    usage_snapshot = usage_snapshots.get(snapshot.game_id)
                    minutes_snapshot = minutes_snapshots_by_game_id.get(snapshot.game_id)
                    contextual_snapshot = snapshot.with_context(
                        opponent_average_allowed=context.opponent_average_allowed.get((snapshot.source_stat_id, metric_name)),
                        opponent_rank=context.opponent_rank.get((snapshot.source_stat_id, metric_name)),
                        pace_proxy=context.game_pace_proxy.get(snapshot.game_id),
                        usage_shift=(
                            snapshot.current_value - snapshot.medium_window.rolling_avg
                            if metric_name == "usage_rate"
                            else (usage_snapshot.current_value - usage_snapshot.medium_window.rolling_avg) if usage_snapshot else None
                        ),
                        minutes_current=minutes_snapshot.current_value if minutes_snapshot else None,
                        minutes_baseline=minutes_snapshot.baseline_value if minutes_snapshot else None,
                    )

                    rolling_metric, rolling_created = _upsert_rolling_metric(
                        db,
                        player_id=player.id,
                        game_id=contextual_snapshot.game_id,
                        source_stat_id=contextual_snapshot.source_stat_id,
                        metric_name=metric_name,
                        snapshot=contextual_snapshot,
                        generated_at=generated_at,
                    )
                    db.flush()
                    _sync_rolling_metric_baseline_samples(
                        db,
                        rolling_metric_id=rolling_metric.id,
                        baseline_stat_ids=contextual_snapshot.baseline_stat_ids,
                    )

                    signal_type = classify_signal(contextual_snapshot, metric_name)
                    signal_score = 0.0
                    score_explanation = ""
                    if signal_type is not None:
                        signal_score, score_explanation = score_signal(
                            contextual_snapshot,
                            signal_type=signal_type,
                            metric_name=metric_name,
                            event_date=contextual_snapshot.event_date,
                            latest_event_date=latest_event_date,
                        )

                    explanation = build_explanation(
                        player.name,
                        metric_name,
                        contextual_snapshot.current_value,
                        contextual_snapshot.baseline_value,
                        contextual_snapshot.z_score,
                        signal_type,
                        snapshot=contextual_snapshot,
                    )

                    narrative = (
                        build_narrative_summary(signal_type, contextual_snapshot, metric_name)
                        if signal_type is not None
                        else None
                    )

                    if signal_type is None:
                        created, updated, deleted = _sync_signal_for_context(
                            db,
                            player=player,
                            game_id=contextual_snapshot.game_id,
                            rolling_metric_id=rolling_metric.id,
                            source_stat_id=contextual_snapshot.source_stat_id,
                            metric_name=metric_name,
                            signal_type=None,
                            current_value=contextual_snapshot.current_value,
                            baseline_value=contextual_snapshot.baseline_value,
                            z_score=contextual_snapshot.z_score,
                            signal_score=0.0,
                            score_explanation="",
                            explanation=explanation,
                            narrative_summary=None,
                            generated_at=generated_at,
                        )
                    else:
                        signal_candidates.append(
                            PlayerSignalCandidate(
                                player=player,
                                game_id=contextual_snapshot.game_id,
                                rolling_metric_id=rolling_metric.id,
                                source_stat_id=contextual_snapshot.source_stat_id,
                                metric_name=metric_name,
                                signal_type=signal_type,
                                current_value=contextual_snapshot.current_value,
                                baseline_value=contextual_snapshot.baseline_value,
                                z_score=contextual_snapshot.z_score,
                                signal_score=signal_score,
                                score_explanation=score_explanation,
                                explanation=explanation,
                                narrative_summary=narrative,
                                generated_at=generated_at,
                            )
                        )
                        created = updated = deleted = 0

                    result = SignalGenerationResult(
                        created_signals=result.created_signals + created,
                        updated_signals=result.updated_signals + updated,
                        deleted_signals=result.deleted_signals + deleted,
                        created_rolling_metrics=result.created_rolling_metrics + int(rolling_created),
                        updated_rolling_metrics=result.updated_rolling_metrics + int(not rolling_created),
                        deleted_rolling_metrics=result.deleted_rolling_metrics,
                    )

            created, updated, deleted = _sync_player_signal_candidates(db, signal_candidates)
            result = SignalGenerationResult(
                created_signals=result.created_signals + created,
                updated_signals=result.updated_signals + updated,
                deleted_signals=result.deleted_signals + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
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

        result = _generate_team_signals(db, result=result)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise SignalGenerationError(
            "Signal generation failed and transaction was rolled back.",
            partial_result=result,
            cause=exc,
        ) from exc
