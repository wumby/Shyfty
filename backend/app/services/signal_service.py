from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.domain.signals import (
    BASELINE_WINDOW_SIZE,
    baseline_window_label,
    classification_reason,
    importance_label,
    importance_score,
    metric_label,
    movement_pct,
    trend_direction,
)
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.rolling_metric import RollingMetric
from app.models.signal import Signal
from app.models.signal_reaction import SignalReaction
from app.models.team import Team
from app.schemas.reaction import ReactionSummaryRead
from app.schemas.signal import PaginatedSignals, SignalRead, SignalSummaryTemplateInputs
from app.services.reaction_service import get_reaction_summaries, get_user_reactions


def build_signal_read(
    signal: Signal,
    player_name: str,
    team_name: str,
    league_name: str,
    event_date,
    rolling_stddev: Optional[float],
    reaction_summary: Optional[ReactionSummaryRead] = None,
    user_reaction: Optional[str] = None,
) -> SignalRead:
    baseline_window = baseline_window_label()
    movement = movement_pct(signal.current_value, signal.baseline_value)
    direction = trend_direction(signal.current_value, signal.baseline_value)
    readable_metric_label = metric_label(signal.metric_name)
    importance = importance_score(signal.signal_type, signal.z_score)
    return SignalRead(
        id=signal.id,
        player_id=signal.player_id,
        game_id=signal.game_id,
        player_name=player_name,
        team_name=team_name,
        league_name=league_name,
        signal_type=signal.signal_type,
        metric_name=signal.metric_name,
        current_value=signal.current_value,
        baseline_value=signal.baseline_value,
        z_score=signal.z_score,
        explanation=signal.explanation,
        importance=importance,
        importance_label=importance_label(signal.signal_type, signal.z_score),
        baseline_window=baseline_window,
        baseline_window_size=BASELINE_WINDOW_SIZE + 1,
        event_date=event_date,
        movement_pct=movement,
        metric_label=readable_metric_label,
        trend_direction=direction,
        rolling_stddev=rolling_stddev or 0.0,
        classification_reason=classification_reason(signal.signal_type, signal.z_score, rolling_stddev or 0.0, signal.metric_name),
        summary_template="metric_vs_recent_baseline",
        summary_template_inputs=SignalSummaryTemplateInputs(
            current_value=signal.current_value,
            baseline_value=signal.baseline_value,
            movement_pct=movement,
            baseline_window=baseline_window,
            trend_direction=direction,
        ),
        reaction_summary=reaction_summary or ReactionSummaryRead(),
        user_reaction=user_reaction,
        created_at=signal.created_at,
    )


def list_signals(
    db: Session,
    league: Optional[str],
    team: Optional[str],
    player: Optional[str],
    signal_type: Optional[str],
    limit: int = 24,
    before_id: Optional[int] = None,
    current_user_id: Optional[int] = None,
) -> PaginatedSignals:
    query = (
        select(Signal, Player.name, Team.name, League.name, Game.game_date, RollingMetric.rolling_stddev)
        .join(Player, Signal.player_id == Player.id)
        .join(Team, Signal.team_id == Team.id)
        .join(League, Signal.league_id == League.id)
        .join(Game, Signal.game_id == Game.id)
        .outerjoin(
            RollingMetric,
            and_(
                RollingMetric.player_id == Signal.player_id,
                RollingMetric.game_id == Signal.game_id,
                RollingMetric.metric_name == Signal.metric_name,
            ),
        )
        .order_by(Signal.created_at.desc(), Signal.id.desc())
        .limit(limit + 1)
    )

    if league:
        query = query.where(League.name.ilike(league))
    if team:
        query = query.where(Team.name.ilike(f"%{team}%"))
    if player:
        query = query.where(Player.name.ilike(f"%{player}%"))
    if signal_type:
        query = query.where(Signal.signal_type.ilike(signal_type))
    if before_id is not None:
        query = query.where(Signal.id < before_id)

    rows = db.execute(query).all()

    has_more = len(rows) > limit
    rows = rows[:limit]

    signal_ids = [signal.id for signal, *_ in rows]
    reaction_summaries = get_reaction_summaries(db, signal_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, signal_ids=signal_ids)

    items = [
        build_signal_read(
            signal,
            player_name,
            team_name,
            league_name,
            event_date,
            rolling_stddev,
            reaction_summary=reaction_summaries.get(signal.id),
            user_reaction=user_reactions.get(signal.id),
        )
        for signal, player_name, team_name, league_name, event_date, rolling_stddev in rows
    ]

    next_cursor = items[-1].id if has_more and items else None

    return PaginatedSignals(items=items, has_more=has_more, next_cursor=next_cursor)


def list_trending_signals(
    db: Session,
    limit: int = 12,
    current_user_id: Optional[int] = None,
) -> list[SignalRead]:
    """Return signals ranked by importance + recency + total reaction count."""
    reaction_count_subq = (
        select(SignalReaction.signal_id, func.count(SignalReaction.id).label("total_reactions"))
        .group_by(SignalReaction.signal_id)
        .subquery()
    )

    query = (
        select(Signal, Player.name, Team.name, League.name, Game.game_date, RollingMetric.rolling_stddev)
        .join(Player, Signal.player_id == Player.id)
        .join(Team, Signal.team_id == Team.id)
        .join(League, Signal.league_id == League.id)
        .join(Game, Signal.game_id == Game.id)
        .outerjoin(
            RollingMetric,
            and_(
                RollingMetric.player_id == Signal.player_id,
                RollingMetric.game_id == Signal.game_id,
                RollingMetric.metric_name == Signal.metric_name,
            ),
        )
        .outerjoin(reaction_count_subq, reaction_count_subq.c.signal_id == Signal.id)
        .order_by(
            (func.abs(Signal.z_score) + func.coalesce(reaction_count_subq.c.total_reactions, 0)).desc(),
            Signal.created_at.desc(),
        )
        .limit(limit)
    )

    rows = db.execute(query).all()
    signal_ids = [signal.id for signal, *_ in rows]
    reaction_summaries = get_reaction_summaries(db, signal_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, signal_ids=signal_ids)

    return [
        build_signal_read(
            signal,
            player_name,
            team_name,
            league_name,
            event_date,
            rolling_stddev,
            reaction_summary=reaction_summaries.get(signal.id),
            user_reaction=user_reactions.get(signal.id),
        )
        for signal, player_name, team_name, league_name, event_date, rolling_stddev in rows
    ]
