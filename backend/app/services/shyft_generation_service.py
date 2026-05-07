from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from app.domain.shyfts import (
    METRICS_BY_LEAGUE,
    TEAM_METRICS_BY_LEAGUE,
    build_explanation,
    build_metric_snapshots,
    build_narrative_summary,
    classify_shyft,
    score_shyft,
)
from app.models.game import Game
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.shyft import Shyft
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat

MAX_SIGNALS_PER_PLAYER_GAME = 3


@dataclass(frozen=True)
class ShyftGenerationResult:
    created_shyfts: int = 0
    updated_shyfts: int = 0
    deleted_shyfts: int = 0
    created_rolling_metrics: int = 0
    updated_rolling_metrics: int = 0
    deleted_rolling_metrics: int = 0

    @property
    def created_signals(self) -> int:
        return self.created_shyfts

    @property
    def updated_signals(self) -> int:
        return self.updated_shyfts

    @property
    def deleted_signals(self) -> int:
        return self.deleted_shyfts


@dataclass(frozen=True)
class ShyftGenerationContext:
    game_dates: dict[int, object]
    game_pace_proxy: dict[int, float]
    opponent_average_allowed: dict[tuple[int, str], float]
    opponent_rank: dict[tuple[int, str], int]


@dataclass(frozen=True)
class PlayerShyftCandidate:
    player: Player
    game_id: int
    rolling_metric_id: int
    source_stat_id: int
    metric_name: str
    shyft_type: str
    current_value: float
    baseline_value: float
    z_score: float
    shyft_score: float
    score_explanation: str
    explanation: str
    narrative_summary: Optional[str]
    generated_at: datetime


class ShyftGenerationError(RuntimeError):
    def __init__(self, message: str, *, partial_result: ShyftGenerationResult, cause: Exception) -> None:
        super().__init__(message)
        self.partial_result = partial_result
        self.__cause__ = cause


def build_shyft_generation_context(db: Session) -> ShyftGenerationContext:
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

    return ShyftGenerationContext(
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


def _delete_stale_shyfts(db: Session, *, player_id: int, valid_contexts: set[tuple[int, str]]) -> int:
    existing_contexts = db.execute(
        select(Shyft.game_id, Shyft.metric_name).where(Shyft.player_id == player_id).distinct()
    ).all()
    stale_contexts = [context for context in existing_contexts if context not in valid_contexts]
    if not stale_contexts:
        return 0

    deleted = 0
    for game_id, metric_name in stale_contexts:
        deleted += db.execute(
            delete(Shyft).where(
                Shyft.player_id == player_id,
                Shyft.game_id == game_id,
                Shyft.metric_name == metric_name,
            )
        ).rowcount or 0
    return deleted


def _delete_stale_team_shyfts(db: Session, *, team_id: int, valid_contexts: set[tuple[int, str]]) -> int:
    existing_contexts = db.execute(
        select(Shyft.game_id, Shyft.metric_name).where(
            Shyft.team_id == team_id,
            Shyft.subject_type == "team",
        )
    ).all()
    stale_contexts = [context for context in existing_contexts if context not in valid_contexts]
    if not stale_contexts:
        return 0

    deleted = 0
    for game_id, metric_name in stale_contexts:
        deleted += db.execute(
            delete(Shyft).where(
                Shyft.team_id == team_id,
                Shyft.subject_type == "team",
                Shyft.game_id == game_id,
                Shyft.metric_name == metric_name,
            )
        ).rowcount or 0
    return deleted


def _sync_shyft_for_context(
    db: Session,
    *,
    player: Player,
    game_id: int,
    rolling_metric_id: int,
    source_stat_id: int,
    metric_name: str,
    shyft_type: Optional[str],
    current_value: float,
    baseline_value: float,
    z_score: float,
    shyft_score: float,
    score_explanation: str,
    explanation: str,
    narrative_summary: Optional[str],
    generated_at: datetime,
) -> tuple[int, int, int]:
    existing_shyfts = db.execute(
        select(Shyft).where(
            Shyft.player_id == player.id,
            Shyft.game_id == game_id,
            Shyft.metric_name == metric_name,
        )
    ).scalars().all()

    created = 0
    updated = 0
    deleted = 0

    for existing in existing_shyfts:
        if shyft_type is None or existing.shyft_type != shyft_type:
            db.delete(existing)
            deleted += 1

    if shyft_type is None:
        return created, updated, deleted

    current_shyft = next((shyft for shyft in existing_shyfts if shyft.shyft_type == shyft_type), None)
    if current_shyft is None:
        db.add(
            Shyft(
                player_id=player.id,
                game_id=game_id,
                rolling_metric_id=rolling_metric_id,
                source_stat_id=source_stat_id,
                source_team_stat_id=None,
                team_id=player.team_id,
                league_id=player.league_id,
                subject_type="player",
                shyft_type=shyft_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=z_score,
                shyft_score=shyft_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative_summary,
                created_at=generated_at,
            )
        )
        created += 1
        return created, updated, deleted

    current_shyft.team_id = player.team_id
    current_shyft.league_id = player.league_id
    current_shyft.subject_type = "player"
    current_shyft.rolling_metric_id = rolling_metric_id
    current_shyft.source_stat_id = source_stat_id
    current_shyft.source_team_stat_id = None
    current_shyft.current_value = current_value
    current_shyft.baseline_value = baseline_value
    current_shyft.z_score = z_score
    current_shyft.shyft_score = shyft_score
    current_shyft.score_explanation = score_explanation
    current_shyft.explanation = explanation
    current_shyft.narrative_summary = narrative_summary
    updated += 1
    return created, updated, deleted


def _sync_player_shyft_candidates(
    db: Session,
    candidates: list[PlayerShyftCandidate],
) -> tuple[int, int, int]:
    by_game: dict[int, list[PlayerShyftCandidate]] = {}
    for candidate in candidates:
        by_game.setdefault(candidate.game_id, []).append(candidate)

    created = 0
    updated = 0
    deleted = 0
    for game_candidates in by_game.values():
        ranked = sorted(game_candidates, key=lambda candidate: candidate.shyft_score, reverse=True)
        kept_keys = {(candidate.game_id, candidate.metric_name) for candidate in ranked[:MAX_SIGNALS_PER_PLAYER_GAME]}
        for candidate in ranked:
            shyft_type = (
                candidate.shyft_type
                if (candidate.game_id, candidate.metric_name) in kept_keys
                else None
            )
            candidate_created, candidate_updated, candidate_deleted = _sync_shyft_for_context(
                db,
                player=candidate.player,
                game_id=candidate.game_id,
                rolling_metric_id=candidate.rolling_metric_id,
                source_stat_id=candidate.source_stat_id,
                metric_name=candidate.metric_name,
                shyft_type=shyft_type,
                current_value=candidate.current_value,
                baseline_value=candidate.baseline_value,
                z_score=candidate.z_score,
                shyft_score=candidate.shyft_score if shyft_type is not None else 0.0,
                score_explanation=candidate.score_explanation if shyft_type is not None else "",
                explanation=candidate.explanation,
                narrative_summary=candidate.narrative_summary if shyft_type is not None else None,
                generated_at=candidate.generated_at,
            )
            created += candidate_created
            updated += candidate_updated
            deleted += candidate_deleted
    return created, updated, deleted


def _sync_team_shyft_for_context(
    db: Session,
    *,
    team: Team,
    game_id: int,
    source_team_stat_id: int,
    metric_name: str,
    shyft_type: Optional[str],
    current_value: float,
    baseline_value: float,
    z_score: float,
    shyft_score: float,
    score_explanation: str,
    explanation: str,
    narrative_summary: Optional[str],
    generated_at: datetime,
) -> tuple[int, int, int]:
    existing_shyfts = db.execute(
        select(Shyft).where(
            Shyft.team_id == team.id,
            Shyft.subject_type == "team",
            Shyft.game_id == game_id,
            Shyft.metric_name == metric_name,
        )
    ).scalars().all()

    created = 0
    updated = 0
    deleted = 0

    for existing in existing_shyfts:
        if shyft_type is None or existing.shyft_type != shyft_type:
            db.delete(existing)
            deleted += 1

    if shyft_type is None:
        return created, updated, deleted

    current_shyft = next(
        (
            shyft
            for shyft in existing_shyfts
            if shyft.metric_name == metric_name and shyft.shyft_type == shyft_type
        ),
        None,
    )
    if current_shyft is None:
        db.add(
            Shyft(
                player_id=None,
                game_id=game_id,
                rolling_metric_id=None,
                source_stat_id=None,
                source_team_stat_id=source_team_stat_id,
                team_id=team.id,
                league_id=team.league_id,
                subject_type="team",
                shyft_type=shyft_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=z_score,
                shyft_score=shyft_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative_summary,
                created_at=generated_at,
            )
        )
        created += 1
        return created, updated, deleted

    current_shyft.player_id = None
    current_shyft.rolling_metric_id = None
    current_shyft.source_stat_id = None
    current_shyft.source_team_stat_id = source_team_stat_id
    current_shyft.team_id = team.id
    current_shyft.league_id = team.league_id
    current_shyft.subject_type = "team"
    current_shyft.current_value = current_value
    current_shyft.baseline_value = baseline_value
    current_shyft.z_score = z_score
    current_shyft.shyft_score = shyft_score
    current_shyft.score_explanation = score_explanation
    current_shyft.explanation = explanation
    current_shyft.narrative_summary = narrative_summary
    updated += 1
    return created, updated, deleted


def _generate_team_shyfts(
    db: Session,
    *,
    result: ShyftGenerationResult,
    team_ids: Optional[list[int]] = None,
) -> ShyftGenerationResult:
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
                severity = classify_shyft(snapshot, metric_name)
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
            shyft_type = classify_shyft(snapshot, metric_name)
            if shyft_type is None:
                continue
            generated_at = datetime.utcnow()
            valid_contexts.add((game_id, metric_name))
            explanation = build_explanation(
                team.name,
                metric_name,
                current_value,
                baseline_value,
                snapshot.z_score,
                shyft_type,
                snapshot=snapshot,
            )
            narrative = build_narrative_summary(shyft_type, snapshot, metric_name)
            shyft_score, score_explanation = score_shyft(
                snapshot,
                shyft_type=shyft_type,
                metric_name=metric_name,
                event_date=snapshot.event_date,
                latest_event_date=None,
            )
            created, updated, deleted = _sync_team_shyft_for_context(
                db,
                team=team,
                game_id=game_id,
                source_team_stat_id=stat.id,
                metric_name=metric_name,
                shyft_type=shyft_type,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=snapshot.z_score,
                shyft_score=shyft_score,
                score_explanation=score_explanation,
                explanation=explanation,
                narrative_summary=narrative,
                generated_at=generated_at,
            )
            result = ShyftGenerationResult(
                created_shyfts=result.created_shyfts + created,
                updated_shyfts=result.updated_shyfts + updated,
                deleted_shyfts=result.deleted_shyfts + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics,
            )

        deleted_shyfts = _delete_stale_team_shyfts(db, team_id=team.id, valid_contexts=valid_contexts)
        result = ShyftGenerationResult(
            created_shyfts=result.created_shyfts,
            updated_shyfts=result.updated_shyfts,
            deleted_shyfts=result.deleted_shyfts + deleted_shyfts,
            created_rolling_metrics=result.created_rolling_metrics,
            updated_rolling_metrics=result.updated_rolling_metrics,
            deleted_rolling_metrics=result.deleted_rolling_metrics,
        )

    return result


def generate_shyfts_for_players(
    db: Session,
    player_ids: list[int],
    team_ids: Optional[list[int]] = None,
) -> ShyftGenerationResult:
    """Recompute shyfts for a specific set of players.

    Used by the incremental ingest path after new game data is loaded for known players.
    Builds the full shyft generation context (opponent history, pace) globally so that
    per-player metrics remain accurate relative to the whole league, then restricts
    the computation loop to the provided player IDs.

    Future Kafka consumer plug-in point:
        After a stream consumer processes a game event and loads it via
        load_nba_games_incremental(), it calls this function with the IDs of the
        players whose stats just changed. Signals are updated in near-real-time
        without reprocessing the entire player roster.

    Args:
        player_ids: internal DB player IDs whose shyfts should be regenerated.
    """
    if not player_ids and not team_ids:
        return ShyftGenerationResult()

    result = ShyftGenerationResult()
    try:
        context = build_shyft_generation_context(db)
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
            shyft_candidates: list[PlayerShyftCandidate] = []

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

                    shyft_type = classify_shyft(contextual_snapshot, metric_name)
                    shyft_score = 0.0
                    score_explanation = ""
                    if shyft_type is not None:
                        shyft_score, score_explanation = score_shyft(
                            contextual_snapshot,
                            shyft_type=shyft_type,
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
                        shyft_type,
                        snapshot=contextual_snapshot,
                    )

                    narrative = (
                        build_narrative_summary(shyft_type, contextual_snapshot, metric_name)
                        if shyft_type is not None
                        else None
                    )

                    if shyft_type is None:
                        created, updated, deleted = _sync_shyft_for_context(
                            db,
                            player=player,
                            game_id=contextual_snapshot.game_id,
                            rolling_metric_id=rolling_metric.id,
                            source_stat_id=contextual_snapshot.source_stat_id,
                            metric_name=metric_name,
                            shyft_type=None,
                            current_value=contextual_snapshot.current_value,
                            baseline_value=contextual_snapshot.baseline_value,
                            z_score=contextual_snapshot.z_score,
                            shyft_score=0.0,
                            score_explanation="",
                            explanation=explanation,
                            narrative_summary=None,
                            generated_at=generated_at,
                        )
                    else:
                        shyft_candidates.append(
                            PlayerShyftCandidate(
                                player=player,
                                game_id=contextual_snapshot.game_id,
                                rolling_metric_id=rolling_metric.id,
                                source_stat_id=contextual_snapshot.source_stat_id,
                                metric_name=metric_name,
                                shyft_type=shyft_type,
                                current_value=contextual_snapshot.current_value,
                                baseline_value=contextual_snapshot.baseline_value,
                                z_score=contextual_snapshot.z_score,
                                shyft_score=shyft_score,
                                score_explanation=score_explanation,
                                explanation=explanation,
                                narrative_summary=narrative,
                                generated_at=generated_at,
                            )
                        )
                        created = updated = deleted = 0

                    result = ShyftGenerationResult(
                        created_shyfts=result.created_shyfts + created,
                        updated_shyfts=result.updated_shyfts + updated,
                        deleted_shyfts=result.deleted_shyfts + deleted,
                        created_rolling_metrics=result.created_rolling_metrics + int(rolling_created),
                        updated_rolling_metrics=result.updated_rolling_metrics + int(not rolling_created),
                        deleted_rolling_metrics=result.deleted_rolling_metrics,
                    )

            created, updated, deleted = _sync_player_shyft_candidates(db, shyft_candidates)
            result = ShyftGenerationResult(
                created_shyfts=result.created_shyfts + created,
                updated_shyfts=result.updated_shyfts + updated,
                deleted_shyfts=result.deleted_shyfts + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics,
            )
            deleted_rolling_metrics = _delete_stale_rolling_metrics(db, player_id=player.id, valid_contexts=valid_contexts)
            deleted_shyfts = _delete_stale_shyfts(db, player_id=player.id, valid_contexts=valid_contexts)
            result = ShyftGenerationResult(
                created_shyfts=result.created_shyfts,
                updated_shyfts=result.updated_shyfts,
                deleted_shyfts=result.deleted_shyfts + deleted_shyfts,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics + deleted_rolling_metrics,
            )

        result = _generate_team_shyfts(db, result=result, team_ids=team_ids)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise ShyftGenerationError(
            "Incremental shyft generation failed and transaction was rolled back.",
            partial_result=result,
            cause=exc,
        ) from exc


def generate_shyfts(db: Session) -> ShyftGenerationResult:
    result = ShyftGenerationResult()
    try:
        context = build_shyft_generation_context(db)
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
            shyft_candidates: list[PlayerShyftCandidate] = []

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

                    shyft_type = classify_shyft(contextual_snapshot, metric_name)
                    shyft_score = 0.0
                    score_explanation = ""
                    if shyft_type is not None:
                        shyft_score, score_explanation = score_shyft(
                            contextual_snapshot,
                            shyft_type=shyft_type,
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
                        shyft_type,
                        snapshot=contextual_snapshot,
                    )

                    narrative = (
                        build_narrative_summary(shyft_type, contextual_snapshot, metric_name)
                        if shyft_type is not None
                        else None
                    )

                    if shyft_type is None:
                        created, updated, deleted = _sync_shyft_for_context(
                            db,
                            player=player,
                            game_id=contextual_snapshot.game_id,
                            rolling_metric_id=rolling_metric.id,
                            source_stat_id=contextual_snapshot.source_stat_id,
                            metric_name=metric_name,
                            shyft_type=None,
                            current_value=contextual_snapshot.current_value,
                            baseline_value=contextual_snapshot.baseline_value,
                            z_score=contextual_snapshot.z_score,
                            shyft_score=0.0,
                            score_explanation="",
                            explanation=explanation,
                            narrative_summary=None,
                            generated_at=generated_at,
                        )
                    else:
                        shyft_candidates.append(
                            PlayerShyftCandidate(
                                player=player,
                                game_id=contextual_snapshot.game_id,
                                rolling_metric_id=rolling_metric.id,
                                source_stat_id=contextual_snapshot.source_stat_id,
                                metric_name=metric_name,
                                shyft_type=shyft_type,
                                current_value=contextual_snapshot.current_value,
                                baseline_value=contextual_snapshot.baseline_value,
                                z_score=contextual_snapshot.z_score,
                                shyft_score=shyft_score,
                                score_explanation=score_explanation,
                                explanation=explanation,
                                narrative_summary=narrative,
                                generated_at=generated_at,
                            )
                        )
                        created = updated = deleted = 0

                    result = ShyftGenerationResult(
                        created_shyfts=result.created_shyfts + created,
                        updated_shyfts=result.updated_shyfts + updated,
                        deleted_shyfts=result.deleted_shyfts + deleted,
                        created_rolling_metrics=result.created_rolling_metrics + int(rolling_created),
                        updated_rolling_metrics=result.updated_rolling_metrics + int(not rolling_created),
                        deleted_rolling_metrics=result.deleted_rolling_metrics,
                    )

            created, updated, deleted = _sync_player_shyft_candidates(db, shyft_candidates)
            result = ShyftGenerationResult(
                created_shyfts=result.created_shyfts + created,
                updated_shyfts=result.updated_shyfts + updated,
                deleted_shyfts=result.deleted_shyfts + deleted,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics,
            )
            deleted_rolling_metrics = _delete_stale_rolling_metrics(db, player_id=player.id, valid_contexts=valid_contexts)
            deleted_shyfts = _delete_stale_shyfts(db, player_id=player.id, valid_contexts=valid_contexts)
            result = ShyftGenerationResult(
                created_shyfts=result.created_shyfts,
                updated_shyfts=result.updated_shyfts,
                deleted_shyfts=result.deleted_shyfts + deleted_shyfts,
                created_rolling_metrics=result.created_rolling_metrics,
                updated_rolling_metrics=result.updated_rolling_metrics,
                deleted_rolling_metrics=result.deleted_rolling_metrics + deleted_rolling_metrics,
            )

        result = _generate_team_shyfts(db, result=result)
        db.commit()
        return result
    except Exception as exc:
        db.rollback()
        raise ShyftGenerationError(
            "Shyft generation failed and transaction was rolled back.",
            partial_result=result,
            cause=exc,
        ) from exc
