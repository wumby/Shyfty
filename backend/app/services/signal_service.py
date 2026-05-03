from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.domain.signals import (
    BASELINE_WINDOW_SIZE,
    baseline_window_label,
    classification_reason,
    importance_label,
    importance_label_for_score,
    importance_score,
    MetricSnapshot,
    WindowSnapshot,
    deviation_from_expected,
    meaningful_movement_pct,
    metric_label,
    stat_signal_config,
    performance_ratio,
    signal_gate_trace,
    trend_direction,
)
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.signal import Signal
from app.models.signal_comment import SignalComment
from app.models.signal_reaction import SignalReaction
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user_follow import UserFollow
from app.schemas.reaction import ReactionAggregateRead, ReactionSummaryRead, ShyftReaction
from app.schemas.signal import (
    CascadeContributorRead,
    CascadePlayerRead,
    CascadeSignalRead,
    CascadeTriggerRead,
    FeedContextRead,
    FeedItemRead,
    PaginatedSignals,
    SignalDebugTraceRead,
    SignalRead,
    SignalSummaryTemplateInputs,
)
from app.services.reaction_service import get_reaction_summaries, get_user_reactions

SORT_MODE_NEWEST = "newest"
SORT_MODE_IMPORTANT = "most_important"
SORT_MODE_DEVIATION = "biggest_deviation"
SORT_MODE_DISCUSSED = "most_discussed"

FEED_MODE_ALL = "all"
FEED_MODE_FOLLOWING = "following"
FEED_MODE_FOR_YOU = "for_you"
EXCLUDED_SIGNAL_TYPES = {"CONSISTENCY"}
CASCADE_TRIGGER_STATS = {"minutes", "minutes_played"}
CASCADE_ALLOWED_CONTRIBUTOR_STATS = {
    "points",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "usage_rate",
    "minutes",
    "minutes_played",
}
CASCADE_MIN_TRIGGER_DROP_PCT = -50.0
CASCADE_MAX_CONTRIBUTORS = 5
CASCADE_MIN_CONTRIBUTOR_SCORE = 5.0


def _deviation_expr():
    return func.abs(Signal.current_value - Signal.baseline_value)


def _severity_order_expr():
    return case(
        (Signal.signal_type == "OUTLIER", 3),
        (Signal.signal_type == "SWING", 2),
        (Signal.signal_type == "SHIFT", 1),
        else_=0,
    )


def _severity_filter_expr(signal_type: str):
    return Signal.signal_type.ilike(signal_type)


def effective_metric_to_snapshot(signal: Signal, rolling_metric: Optional[RollingMetric]) -> MetricSnapshot:
    short_values = rolling_metric.short_values if rolling_metric and rolling_metric.short_values else [signal.baseline_value]
    medium_values = rolling_metric.medium_values if rolling_metric and rolling_metric.medium_values else short_values
    season_values = rolling_metric.season_values if rolling_metric and rolling_metric.season_values else medium_values
    return MetricSnapshot(
        game_id=signal.game_id,
        source_stat_id=signal.source_stat_id or 0,
        event_date=None,
        baseline_stat_ids=[],
        current_value=signal.current_value,
        baseline_value=signal.baseline_value,
        rolling_stddev=rolling_metric.short_rolling_stddev if rolling_metric and rolling_metric.short_rolling_stddev is not None else 0.0,
        z_score=signal.z_score,
        short_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in short_values],
            rolling_avg=rolling_metric.short_rolling_avg if rolling_metric and rolling_metric.short_rolling_avg is not None else signal.baseline_value,
            rolling_stddev=rolling_metric.short_rolling_stddev if rolling_metric and rolling_metric.short_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.short_z_score if rolling_metric and rolling_metric.short_z_score is not None else signal.z_score,
        ),
        medium_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in medium_values],
            rolling_avg=rolling_metric.medium_rolling_avg if rolling_metric and rolling_metric.medium_rolling_avg is not None else signal.baseline_value,
            rolling_stddev=rolling_metric.medium_rolling_stddev if rolling_metric and rolling_metric.medium_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.medium_z_score if rolling_metric and rolling_metric.medium_z_score is not None else signal.z_score,
        ),
        season_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in season_values],
            rolling_avg=rolling_metric.season_rolling_avg if rolling_metric and rolling_metric.season_rolling_avg is not None else signal.baseline_value,
            rolling_stddev=rolling_metric.season_rolling_stddev if rolling_metric and rolling_metric.season_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.season_z_score if rolling_metric and rolling_metric.season_z_score is not None else signal.z_score,
        ),
        ewma=rolling_metric.ewma if rolling_metric and rolling_metric.ewma is not None else signal.baseline_value,
        recent_delta=rolling_metric.recent_delta if rolling_metric and rolling_metric.recent_delta is not None else 0.0,
        trend_slope=rolling_metric.trend_slope if rolling_metric and rolling_metric.trend_slope is not None else 0.0,
        volatility_index=rolling_metric.volatility_index if rolling_metric and rolling_metric.volatility_index is not None else 0.0,
        volatility_delta=rolling_metric.volatility_delta if rolling_metric and rolling_metric.volatility_delta is not None else 0.0,
        opponent_average_allowed=rolling_metric.opponent_average_allowed if rolling_metric else None,
        opponent_rank=rolling_metric.opponent_rank if rolling_metric else None,
        pace_proxy=rolling_metric.pace_proxy if rolling_metric else None,
        usage_shift=rolling_metric.usage_shift if rolling_metric else None,
        high_volatility=bool(rolling_metric.high_volatility) if rolling_metric and rolling_metric.high_volatility is not None else False,
    )


def build_signal_read(
    signal: Signal,
    player_name: Optional[str],
    team_name: str,
    league_name: str,
    event_date,
    rolling_metric: Optional[RollingMetric],
    reaction_summary: Optional[ReactionSummaryRead] = None,
    reactions: Optional[list[ReactionAggregateRead]] = None,
    user_reaction: Optional[str] = None,
    user_reactions: Optional[list[str]] = None,
    comment_count: int = 0,
    opponent: Optional[str] = None,
    home_away: Optional[str] = None,
    game_result: Optional[str] = None,
    final_score: Optional[str] = None,
    streak: int = 1,
) -> SignalRead:
    baseline_window = baseline_window_label()
    movement = meaningful_movement_pct(signal.metric_name, signal.current_value, signal.baseline_value)
    performance = performance_ratio(signal.current_value, signal.baseline_value)
    deviation = deviation_from_expected(signal.current_value, signal.baseline_value)
    severity = signal.signal_type
    direction = trend_direction(signal.current_value, signal.baseline_value)
    readable_metric_label = metric_label(signal.metric_name)
    snapshot = effective_metric_to_snapshot(signal, rolling_metric)
    debug_trace = signal_gate_trace(snapshot, signal.metric_name)
    signal_score = round(signal.signal_score or importance_score(severity, signal.z_score, deviation), 1)
    rolling_stddev = (
        rolling_metric.short_rolling_stddev
        if rolling_metric and rolling_metric.short_rolling_stddev is not None
        else (rolling_metric.rolling_stddev if rolling_metric is not None else 0.0)
    )
    reaction_entries = reactions or []
    reaction_summary_value = reaction_summary or ReactionSummaryRead(
        shyft_up=sum(item.count for item in reaction_entries if item.type == ShyftReaction.SHYFT_UP),
        shyft_down=sum(item.count for item in reaction_entries if item.type == ShyftReaction.SHYFT_DOWN),
        shyft_eye=sum(item.count for item in reaction_entries if item.type == ShyftReaction.SHYFT_EYE),
    )
    user_reactions_value = user_reactions or ([user_reaction] if user_reaction else [])

    return SignalRead(
        id=signal.id,
        subject_type=signal.subject_type,
        player_id=signal.player_id,
        team_id=signal.team_id,
        game_id=signal.game_id,
        player_name=player_name or team_name,
        team_name=team_name,
        league_name=league_name,
        signal_type=severity,
        severity=severity,
        metric_name=signal.metric_name,
        current_value=signal.current_value,
        baseline_value=signal.baseline_value,
        performance=performance,
        deviation=deviation,
        z_score=signal.z_score,
        signal_score=signal_score,
        score_explanation=signal.score_explanation,
        explanation=signal.explanation,
        importance=signal_score,
        importance_label=importance_label_for_score(signal_score),
        baseline_window=baseline_window,
        baseline_window_size=(rolling_metric.short_window_size if rolling_metric and rolling_metric.short_window_size else BASELINE_WINDOW_SIZE),
        event_date=event_date,
        movement_pct=movement,
        metric_label=readable_metric_label,
        trend_direction=direction,
        rolling_stddev=rolling_stddev,
        opponent=opponent,
        home_away=home_away,
        game_result=game_result,
        final_score=final_score,
        classification_reason=classification_reason(severity, snapshot, signal.metric_name),
        debug_trace=SignalDebugTraceRead(**debug_trace),
        summary_template="metric_vs_recent_baseline",
        summary_template_inputs=SignalSummaryTemplateInputs(
            current_value=signal.current_value,
            baseline_value=signal.baseline_value,
            movement_pct=movement,
            baseline_window=baseline_window,
            trend_direction=direction,
            medium_window_z=rolling_metric.medium_z_score if rolling_metric else None,
            season_window_z=rolling_metric.season_z_score if rolling_metric else None,
            trend_slope=rolling_metric.trend_slope if rolling_metric else None,
            usage_shift=rolling_metric.usage_shift if rolling_metric else None,
        ),
        streak=streak,
        reaction_summary=reaction_summary_value,
        user_reaction=user_reaction,
        reactions=reaction_entries,
        user_reactions=user_reactions_value,
        comment_count=comment_count,
        created_at=signal.created_at,
    )


def _comment_count_subquery():
    base_signal = aliased(Signal)
    comment_signal = aliased(Signal)
    same_signal_group = and_(
        comment_signal.game_id == base_signal.game_id,
        comment_signal.subject_type == base_signal.subject_type,
        or_(
            and_(base_signal.player_id.is_not(None), comment_signal.player_id == base_signal.player_id),
            and_(
                base_signal.player_id.is_(None),
                comment_signal.player_id.is_(None),
                comment_signal.team_id == base_signal.team_id,
            ),
        ),
    )
    return (
        select(base_signal.id.label("signal_id"), func.count(SignalComment.id).label("comment_count"))
        .select_from(base_signal)
        .outerjoin(comment_signal, same_signal_group)
        .outerjoin(SignalComment, SignalComment.signal_id == comment_signal.id)
        .group_by(base_signal.id)
        .subquery()
    )


def _reaction_count_subquery():
    return (
        select(SignalReaction.signal_id, func.count(SignalReaction.id).label("reaction_count"))
        .group_by(SignalReaction.signal_id)
        .subquery()
    )


def _base_signal_query():
    comment_count_subq = _comment_count_subquery()
    reaction_count_subq = _reaction_count_subquery()
    home_team = aliased(Team)
    away_team = aliased(Team)
    signal_team_stat = aliased(TeamGameStat)
    opponent_team_stat = aliased(TeamGameStat)
    return (
        select(
            Signal,
            Player.name,
            Team.name,
            League.name,
            Game.game_date,
            RollingMetric,
            func.coalesce(comment_count_subq.c.comment_count, 0).label("comment_count"),
            func.coalesce(reaction_count_subq.c.reaction_count, 0).label("reaction_count"),
            PlayerGameStat.plus_minus,
            Game.home_team_id,
            Game.away_team_id,
            home_team.name.label("home_team_name"),
            away_team.name.label("away_team_name"),
            TeamGameStat.opponent_name,
            TeamGameStat.home_away,
            signal_team_stat.points.label("signal_team_points"),
            opponent_team_stat.points.label("opponent_team_points"),
        )
        .outerjoin(Player, Signal.player_id == Player.id)
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
        .outerjoin(PlayerGameStat, PlayerGameStat.id == Signal.source_stat_id)
        .outerjoin(TeamGameStat, TeamGameStat.id == Signal.source_team_stat_id)
        .outerjoin(
            signal_team_stat,
            and_(signal_team_stat.game_id == Signal.game_id, signal_team_stat.team_id == Signal.team_id),
        )
        .outerjoin(
            opponent_team_stat,
            and_(opponent_team_stat.game_id == Signal.game_id, opponent_team_stat.team_id != Signal.team_id),
        )
        .outerjoin(home_team, Game.home_team_id == home_team.id)
        .outerjoin(away_team, Game.away_team_id == away_team.id)
        .outerjoin(comment_count_subq, comment_count_subq.c.signal_id == Signal.id)
        .outerjoin(reaction_count_subq, reaction_count_subq.c.signal_id == Signal.id)
        .where(~Signal.signal_type.in_(EXCLUDED_SIGNAL_TYPES))
    )


def _get_engagement_context(db: Session, user_id: int) -> dict[str, object]:
    followed_rows = db.execute(
        select(UserFollow.entity_type, UserFollow.entity_id).where(UserFollow.user_id == user_id)
    ).all()
    followed_players = {entity_id for entity_type, entity_id in followed_rows if entity_type == "player"}
    followed_teams = {entity_id for entity_type, entity_id in followed_rows if entity_type == "team"}

    reaction_rows = db.execute(
        select(Signal.player_id, Signal.team_id, Signal.metric_name)
        .join(SignalReaction, SignalReaction.signal_id == Signal.id)
        .where(SignalReaction.user_id == user_id)
    ).all()
    comment_rows = db.execute(
        select(Signal.player_id, Signal.team_id, Signal.metric_name)
        .join(SignalComment, SignalComment.signal_id == Signal.id)
        .where(SignalComment.user_id == user_id)
    ).all()
    metric_names = {metric_name for *_, metric_name in [*reaction_rows, *comment_rows]}
    engaged_players = {player_id for player_id, *_ in [*reaction_rows, *comment_rows]}
    engaged_teams = {team_id for _, team_id, _ in [*reaction_rows, *comment_rows]}

    return {
        "followed_players": followed_players | engaged_players,
        "followed_teams": followed_teams | engaged_teams,
        "metric_names": metric_names,
    }


def _apply_sort(query, sort_mode: str):
    deviation_expr = _deviation_expr()
    ranked_order = (
        func.coalesce(Signal.signal_score, 0).desc(),
        _severity_order_expr().desc(),
        deviation_expr.desc(),
        Game.game_date.desc(),
        Signal.id.desc(),
    )
    if sort_mode == SORT_MODE_IMPORTANT:
        return query.order_by(*ranked_order)
    if sort_mode == SORT_MODE_DEVIATION:
        return query.order_by(*ranked_order)
    return query.order_by(Game.game_date.desc(), Signal.id.desc())


def _compute_streaks(
    db: Session,
    signal_info: list[tuple[int, Optional[int], str, str, date]],
) -> dict[int, int]:
    """
    signal_info: [(signal_id, player_id, metric_name, signal_type, event_date), ...]
    Returns {signal_id: streak_count}.
    Streak = consecutive prior games (by date, going back) where the same player
    had the same signal_type for the same metric, with no gap of a different type.
    """
    player_metric_pairs = {
        (pid, metric)
        for _, pid, metric, _, _ in signal_info
        if pid is not None
    }
    if not player_metric_pairs:
        return {sig_id: 1 for sig_id, *_ in signal_info}

    history_rows = db.execute(
        select(Signal.player_id, Signal.metric_name, Signal.signal_type, Game.game_date)
        .join(Game, Signal.game_id == Game.id)
        .where(~Signal.signal_type.in_(EXCLUDED_SIGNAL_TYPES))
        .where(or_(*[
            and_(Signal.player_id == pid, Signal.metric_name == metric)
            for pid, metric in player_metric_pairs
        ]))
        .order_by(Game.game_date.desc(), Signal.id.desc())
    ).all()

    history: dict[tuple, list[tuple[str, date]]] = defaultdict(list)
    for player_id, metric_name, sig_type, game_date in history_rows:
        history[(player_id, metric_name)].append((sig_type, game_date))

    result: dict[int, int] = {}
    for sig_id, player_id, metric_name, signal_type, event_date in signal_info:
        if player_id is None:
            result[sig_id] = 1
            continue
        relevant = [(st, gd) for st, gd in history[(player_id, metric_name)] if gd <= event_date]
        count = 0
        for st, _ in relevant:
            if st == signal_type:
                count += 1
            else:
                break
        result[sig_id] = max(count, 1)

    return result


def _build_signal_items(rows, db: Session, current_user_id: Optional[int]) -> list[SignalRead]:
    signal_ids = [signal.id for signal, *_ in rows]
    reaction_summaries = get_reaction_summaries(db, signal_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, signal_ids=signal_ids)

    signal_info = [
        (signal.id, signal.player_id, signal.metric_name, signal.signal_type, event_date)
        for signal, _player_name, _team_name, _league_name, event_date, *_ in rows
    ]
    streaks = _compute_streaks(db, signal_info)

    items: list[SignalRead] = []
    for (
        signal,
        player_name,
        team_name,
        league_name,
        event_date,
        rolling_metric,
        comment_count,
        _reaction_count,
        plus_minus,
        home_team_id,
        away_team_id,
        home_team_name,
        away_team_name,
        team_stat_opponent_name,
        team_stat_home_away,
        signal_team_points,
        opponent_team_points,
    ) in rows:
        is_home = signal.team_id == home_team_id
        opponent = team_stat_opponent_name or (away_team_name if is_home else home_team_name)
        home_away = team_stat_home_away or ("vs" if is_home else "@")
        final_score = (
            f"{int(signal_team_points)}-{int(opponent_team_points)}"
            if signal_team_points is not None and opponent_team_points is not None
            else None
        )
        score_result = (
            "W"
            if signal_team_points is not None and opponent_team_points is not None and signal_team_points > opponent_team_points
            else "L"
            if signal_team_points is not None and opponent_team_points is not None and signal_team_points < opponent_team_points
            else None
        )
        game_result = score_result or (None if signal.subject_type == "team" else ("W" if plus_minus and plus_minus > 0 else "L" if plus_minus and plus_minus < 0 else None))

        current_user_reactions = sorted(user_reactions.get(signal.id, set()))
        items.append(
            build_signal_read(
                signal,
                player_name,
                team_name,
                league_name,
                event_date,
                rolling_metric,
                reactions=reaction_summaries.get(signal.id),
                user_reactions=current_user_reactions,
                user_reaction=next(iter(user_reactions.get(signal.id, set())), None),
                comment_count=comment_count,
                opponent=opponent,
                home_away=home_away,
                game_result=game_result,
                final_score=final_score,
                streak=streaks.get(signal.id, 1),
            )
        )
    return items


def _delta_percent(item: SignalRead) -> Optional[float]:
    if item.movement_pct is not None:
        return item.movement_pct
    if abs(item.baseline_value) < 0.05:
        return None
    return ((item.current_value - item.baseline_value) / item.baseline_value) * 100


def _is_cascade_trigger(item: SignalRead) -> bool:
    if item.subject_type != "player" or item.player_id is None:
        return False
    if item.metric_name not in CASCADE_TRIGGER_STATS:
        return False
    if item.current_value >= item.baseline_value:
        return False
    drop_pct = _delta_percent(item)
    return item.current_value <= 0.5 or (drop_pct is not None and drop_pct <= CASCADE_MIN_TRIGGER_DROP_PCT)


def _is_cascade_contributor(item: SignalRead, trigger: SignalRead) -> bool:
    if item.subject_type != "player" or item.player_id is None:
        return False
    if item.game_id != trigger.game_id or item.team_id != trigger.team_id or item.player_id == trigger.player_id:
        return False
    if item.metric_name not in CASCADE_ALLOWED_CONTRIBUTOR_STATS:
        return False
    if item.current_value <= item.baseline_value:
        return False
    config = stat_signal_config(item.metric_name)
    if item.current_value - item.baseline_value < config.min_delta:
        return False
    return item.signal_score >= CASCADE_MIN_CONTRIBUTOR_SCORE


def _cascade_rank_key(item: SignalRead) -> tuple[float, float, float]:
    delta_pct = _delta_percent(item)
    return (
        item.signal_score,
        abs(delta_pct) if delta_pct is not None else 0.0,
        abs(item.z_score),
    )


def _trigger_read(item: SignalRead) -> CascadeTriggerRead:
    return CascadeTriggerRead(
        player=CascadePlayerRead(id=item.player_id, name=item.player_name),
        signal_id=item.id,
        stat=item.metric_name,
        metric_label=item.metric_label,
        delta=item.current_value - item.baseline_value,
        delta_percent=_delta_percent(item),
        signal_type=item.signal_type,
        signal_score=item.signal_score,
    )


def _contributor_read(item: SignalRead) -> CascadeContributorRead:
    return CascadeContributorRead(
        player=CascadePlayerRead(id=item.player_id, name=item.player_name),
        signal_id=item.id,
        stat=item.metric_name,
        metric_label=item.metric_label,
        delta=item.current_value - item.baseline_value,
        delta_percent=_delta_percent(item),
        signal_type=item.signal_type,
        signal_score=item.signal_score,
    )


def _cascade_drop_reason(trigger: SignalRead) -> str:
    drop_pct = _delta_percent(trigger)
    if trigger.current_value <= 0.5:
        return "DNP"
    if drop_pct is not None and drop_pct <= -75:
        return "minutes cratered"
    return "minutes cut"


def _cascade_usage_phrase(metric_name: str) -> str:
    phrases = {
        "points": "scoring",
        "assists": "playmaking",
        "rebounds": "boards",
        "usage_rate": "usage",
        "minutes": "role",
        "minutes_played": "role",
        "steals": "defense",
        "blocks": "rim protection",
        "turnovers": "touches",
    }
    return phrases.get(metric_name, metric_label(metric_name).lower())


def _cascade_summary(trigger: SignalRead, contributors: list[SignalRead]) -> str:
    primary = contributors[0]
    reason = _cascade_drop_reason(trigger)
    primary_phrase = _cascade_usage_phrase(primary.metric_name)
    summary = f"{trigger.player_name} {reason} → {primary.player_name} absorbed primary {primary_phrase}"
    if len(contributors) >= 2:
        secondary = contributors[1]
        secondary_phrase = _cascade_usage_phrase(secondary.metric_name)
        summary += f", {secondary.player_name} secondary {secondary_phrase}"
    return f"{summary}."


def detect_cascade_signals(items: list[SignalRead], *, max_contributors: int = CASCADE_MAX_CONTRIBUTORS) -> list[CascadeSignalRead]:
    cascades: list[CascadeSignalRead] = []
    triggers = [item for item in items if _is_cascade_trigger(item)]
    seen_trigger_keys: set[tuple[int, int, int]] = set()

    for trigger in sorted(triggers, key=_cascade_rank_key, reverse=True):
        trigger_key = (trigger.game_id, trigger.team_id, trigger.player_id or 0)
        if trigger_key in seen_trigger_keys:
            continue
        contributors = [
            item
            for item in items
            if _is_cascade_contributor(item, trigger)
        ]
        contributors = sorted(contributors, key=_cascade_rank_key, reverse=True)
        if not contributors:
            continue
        kept = contributors[:max_contributors]
        seen_trigger_keys.add(trigger_key)
        cascades.append(
            CascadeSignalRead(
                id=f"cascade:{trigger.game_id}:{trigger.team_id}:{trigger.player_id}",
                game_id=trigger.game_id,
                team_id=trigger.team_id,
                team=trigger.team_name,
                league_name=trigger.league_name,
                game_date=trigger.event_date,
                created_at=max([trigger.created_at, *[contributor.created_at for contributor in kept]]),
                trigger=_trigger_read(trigger),
                contributors=[_contributor_read(contributor) for contributor in kept],
                underlying_signals=[trigger, *kept],
                narrative_summary=_cascade_summary(trigger, kept),
            )
        )

    return cascades


def _inject_cascades(items: list[SignalRead]) -> list[FeedItemRead]:
    cascades = detect_cascade_signals(items)
    if not cascades:
        return items

    cascades_by_trigger_id = {cascade.trigger.signal_id: cascade for cascade in cascades}
    grouped_signal_ids = {
        signal.id
        for cascade in cascades
        for signal in cascade.underlying_signals
    }

    feed_items: list[FeedItemRead] = []
    for item in items:
        cascade = cascades_by_trigger_id.get(item.id)
        if cascade is not None:
            feed_items.append(cascade)
            continue
        if item.id in grouped_signal_ids:
            continue
        feed_items.append(item)
    return feed_items


def _personalized_reason(feed_mode: str, current_user_id: Optional[int], items: list[FeedItemRead]) -> Optional[str]:
    if feed_mode == FEED_MODE_FOLLOWING and current_user_id is None:
        return "Sign in to build a following feed."
    if feed_mode == FEED_MODE_FOR_YOU and current_user_id is None:
        return "Sign in to get a feed ranked from your follows and board activity."
    if feed_mode == FEED_MODE_FOLLOWING and not items:
        return "This view will fill in as you follow players or teams."
    if not items:
        return "This view will fill in as you follow players or teams and react to signals."
    if feed_mode == FEED_MODE_FOLLOWING:
        return "Signals from players and teams you follow."
    if feed_mode == FEED_MODE_FOR_YOU:
        return "Ranked from your follows, comments, and reaction history."
    return None


def list_signals(
    db: Session,
    league: Optional[str],
    team: Optional[str],
    player: Optional[str],
    signal_type: Optional[str],
    limit: int = 24,
    before_id: Optional[int] = None,
    current_user_id: Optional[int] = None,
    sort_mode: str = SORT_MODE_NEWEST,
    feed_mode: str = FEED_MODE_ALL,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PaginatedSignals:
    query = _base_signal_query()

    if league:
        query = query.where(League.name.ilike(league))
    if team:
        query = query.where(Team.name.ilike(f"%{team}%"))
    if player:
        query = query.where(Player.name.ilike(f"%{player}%"))
    if signal_type:
        query = query.where(_severity_filter_expr(signal_type))
    if date_from is not None:
        query = query.where(Game.game_date >= date_from)
    if date_to is not None:
        query = query.where(Game.game_date <= date_to)
    if before_id is not None and sort_mode == SORT_MODE_NEWEST and feed_mode == FEED_MODE_ALL:
        query = query.where(Signal.id < before_id)

    if feed_mode == FEED_MODE_FOLLOWING:
        if current_user_id is None:
            return PaginatedSignals(
                items=[],
                has_more=False,
                next_cursor=None,
                feed_context=FeedContextRead(
                    feed_mode=feed_mode,
                    sort_mode=sort_mode,
                    personalization_reason="Sign in to build a following feed.",
                ),
            )
        follow_rows = db.execute(
            select(UserFollow.entity_type, UserFollow.entity_id).where(UserFollow.user_id == current_user_id)
        ).all()
        followed_players = {entity_id for entity_type, entity_id in follow_rows if entity_type == "player"}
        followed_teams = {entity_id for entity_type, entity_id in follow_rows if entity_type == "team"}
        if not followed_players and not followed_teams:
            return PaginatedSignals(
                items=[],
                has_more=False,
                next_cursor=None,
                feed_context=FeedContextRead(
                    feed_mode=feed_mode,
                    sort_mode=sort_mode,
                    personalization_reason=_personalized_reason(feed_mode, current_user_id, []),
                ),
            )
        follow_clauses = []
        if followed_players:
            follow_clauses.append(and_(Signal.subject_type == "player", Signal.player_id.in_(followed_players)))
        if followed_teams:
            follow_clauses.append(and_(Signal.subject_type == "team", Signal.team_id.in_(followed_teams)))
        query = query.where(or_(*follow_clauses))

    elif feed_mode == FEED_MODE_FOR_YOU and current_user_id is not None:
        query = query.limit(max(limit * 5, 120))
        rows = db.execute(_apply_sort(query, SORT_MODE_NEWEST)).all()
        items = _build_signal_items(rows, db, current_user_id)
        preferred = _get_engagement_context(db, current_user_id)

        def score(item: SignalRead) -> float:
            score_value = item.importance
            if item.player_id in preferred["followed_players"]:
                score_value += 8
            if item.team_id in preferred["followed_teams"]:
                score_value += 6
            if item.metric_name in preferred["metric_names"]:
                score_value += 4
            score_value += item.comment_count * 0.7
            score_value += sum(item.reaction_summary.model_dump().values()) * 0.35
            return score_value

        items = sorted(items, key=score, reverse=True)[:limit]
        feed_items = _inject_cascades(items)
        return PaginatedSignals(
            items=feed_items,
            has_more=False,
            next_cursor=None,
            feed_context=FeedContextRead(
                feed_mode=feed_mode,
                sort_mode=sort_mode,
                personalization_reason=_personalized_reason(feed_mode, current_user_id, feed_items),
            ),
        )

    paginated = sort_mode == SORT_MODE_NEWEST and feed_mode == FEED_MODE_ALL
    query_limit = (limit + 1) if paginated else (max(limit * 5, 120) if sort_mode == SORT_MODE_DISCUSSED else limit)
    rows = db.execute(_apply_sort(query, sort_mode).limit(query_limit)).all()

    has_more = paginated and len(rows) > limit
    rows = rows[:limit] if paginated else rows
    items = _build_signal_items(rows, db, current_user_id)
    if sort_mode == SORT_MODE_DISCUSSED:
        items = sorted(
            items,
            key=lambda item: (
                item.comment_count * 2 + sum(item.reaction_summary.model_dump().values()),
                item.created_at,
            ),
            reverse=True,
        )[:limit]
    feed_items = _inject_cascades(items)
    signal_cursor_items = [item for item in feed_items if isinstance(item, SignalRead)]
    next_cursor = signal_cursor_items[-1].id if has_more and signal_cursor_items else (items[-1].id if has_more and items else None)

    return PaginatedSignals(
        items=feed_items,
        has_more=has_more,
        next_cursor=next_cursor,
        feed_context=FeedContextRead(
            feed_mode=feed_mode,
            sort_mode=sort_mode,
            personalization_reason=_personalized_reason(feed_mode, current_user_id, feed_items),
        ),
    )


def list_trending_signals(
    db: Session,
    limit: int = 12,
    current_user_id: Optional[int] = None,
) -> list[SignalRead]:
    page = list_signals(
        db=db,
        league=None,
        team=None,
        player=None,
        signal_type=None,
        limit=limit,
        before_id=None,
        current_user_id=current_user_id,
        sort_mode=SORT_MODE_IMPORTANT,
    )
    return page.items
