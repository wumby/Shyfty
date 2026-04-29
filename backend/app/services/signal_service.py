from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
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
from app.models.user_favorite import UserFavorite
from app.models.user_follow import UserFollow
from app.schemas.reaction import ReactionSummaryRead
from app.schemas.signal import FeedContextRead, FreshnessContextRead, PaginatedSignals, SignalDebugTraceRead, SignalRead, SignalSummaryTemplateInputs
from app.services.favorite_service import get_favorited_signal_ids
from app.services.reaction_service import get_reaction_summaries, get_user_reactions
from app.services.scheduler import get_ingest_state

SORT_MODE_NEWEST = "newest"
SORT_MODE_IMPORTANT = "most_important"
SORT_MODE_DEVIATION = "biggest_deviation"
SORT_MODE_DISCUSSED = "most_discussed"

FEED_MODE_ALL = "all"
FEED_MODE_FOLLOWING = "following"
FEED_MODE_FOR_YOU = "for_you"
EXCLUDED_SIGNAL_TYPES = {"CONSISTENCY"}


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


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _build_freshness(event_date, created_at: datetime) -> FreshnessContextRead:
    ingest_state = get_ingest_state()
    last_updated = _parse_iso(ingest_state.get("last_updated"))
    now = datetime.now(timezone.utc)
    ingest_age_minutes = None
    if last_updated is not None:
        last_updated = last_updated.astimezone(timezone.utc)
        ingest_age_minutes = max(0, int((now - last_updated).total_seconds() // 60))

    event_age_hours = None
    if event_date is not None:
        event_dt = datetime.combine(event_date, datetime.min.time(), tzinfo=timezone.utc)
        event_age_hours = max(0, int((now - event_dt).total_seconds() // 3600))

    if ingest_state.get("status") == "running":
        state = "refreshing"
        label = "Refreshing board data"
        delayed = "A refresh is in progress. Some signal context may shift as the latest ingest completes."
    elif ingest_age_minutes is None:
        state = "unknown"
        label = "Freshness unknown"
        delayed = "Freshness metadata is not available yet. Treat the board as directional until a successful ingest lands."
    elif ingest_age_minutes <= 90:
        state = "fresh"
        label = "Board refreshed recently"
        delayed = None
    elif ingest_age_minutes <= 6 * 60:
        state = "delayed"
        label = "Board is mildly delayed"
        delayed = "This board is still usable, but some game context may lag behind the latest box scores."
    else:
        state = "stale"
        label = "Board freshness is weak"
        delayed = "Signal timing is now materially delayed. Verify the latest box score context before trusting sharp changes."

    coverage = f"Built from the last {BASELINE_WINDOW_SIZE} games"
    if event_age_hours is not None:
        coverage += f"; this game landed about {event_age_hours}h ago."
    else:
        coverage += "."

    return FreshnessContextRead(
        state=state,
        label=label,
        coverage_summary=coverage,
        delayed_data_message=delayed,
        ingest_age_minutes=ingest_age_minutes,
        event_age_hours=event_age_hours,
    )


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
    user_reaction: Optional[str] = None,
    comment_count: int = 0,
    is_favorited: bool = False,
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
        reaction_summary=reaction_summary or ReactionSummaryRead(),
        user_reaction=user_reaction,
        comment_count=comment_count,
        is_favorited=is_favorited,
        created_at=signal.created_at,
        freshness=_build_freshness(event_date, signal.created_at),
    )


def _comment_count_subquery():
    return (
        select(SignalComment.signal_id, func.count(SignalComment.id).label("comment_count"))
        .group_by(SignalComment.signal_id)
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

    favorite_rows = db.execute(
        select(Signal.player_id, Signal.team_id, Signal.metric_name)
        .join(UserFavorite, UserFavorite.signal_id == Signal.id)
        .where(UserFavorite.user_id == user_id)
    ).all()
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
    metric_names = {metric_name for *_, metric_name in [*favorite_rows, *reaction_rows, *comment_rows]}
    engaged_players = {player_id for player_id, *_ in [*favorite_rows, *reaction_rows, *comment_rows]}
    engaged_teams = {team_id for _, team_id, _ in [*favorite_rows, *reaction_rows, *comment_rows]}

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
    favorited_ids = get_favorited_signal_ids(db, user_id=current_user_id, signal_ids=signal_ids)

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

        items.append(
            build_signal_read(
                signal,
                player_name,
                team_name,
                league_name,
                event_date,
                rolling_metric,
                reaction_summary=reaction_summaries.get(signal.id),
                user_reaction=user_reactions.get(signal.id),
                comment_count=comment_count,
                is_favorited=signal.id in favorited_ids,
                opponent=opponent,
                home_away=home_away,
                game_result=game_result,
                final_score=final_score,
                streak=streaks.get(signal.id, 1),
            )
        )
    return items


def _personalized_reason(feed_mode: str, current_user_id: Optional[int], items: list[SignalRead]) -> Optional[str]:
    if feed_mode == FEED_MODE_FOLLOWING and current_user_id is None:
        return "Sign in to build a following feed."
    if feed_mode == FEED_MODE_FOR_YOU and current_user_id is None:
        return "Sign in to get a feed ranked from your saved signals, follows, and board activity."
    if feed_mode == FEED_MODE_FOLLOWING and not items:
        return "This view will fill in as you follow players or teams."
    if not items:
        return "This view will fill in as you follow players or teams and react to signals."
    if feed_mode == FEED_MODE_FOLLOWING:
        return "Signals from players and teams you follow."
    if feed_mode == FEED_MODE_FOR_YOU:
        return "Ranked from your follows, saved signals, comments, and reaction history."
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
    favorited_only: bool = False,
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

    if favorited_only and current_user_id is not None:
        query = query.join(
            UserFavorite,
            and_(UserFavorite.signal_id == Signal.id, UserFavorite.user_id == current_user_id),
        )

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
        return PaginatedSignals(
            items=items,
            has_more=False,
            next_cursor=None,
            feed_context=FeedContextRead(
                feed_mode=feed_mode,
                sort_mode=sort_mode,
                personalization_reason=_personalized_reason(feed_mode, current_user_id, items),
            ),
        )

    paginated = sort_mode == SORT_MODE_NEWEST and feed_mode == FEED_MODE_ALL and not favorited_only
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
    next_cursor = items[-1].id if has_more and items else None

    return PaginatedSignals(
        items=items,
        has_more=has_more,
        next_cursor=next_cursor,
        feed_context=FeedContextRead(
            feed_mode=feed_mode,
            sort_mode=sort_mode,
            personalization_reason=_personalized_reason(feed_mode, current_user_id, items),
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


def list_related_signals(
    db: Session,
    *,
    signal_id: int,
    player_id: Optional[int],
    team_id: int,
    metric_name: str,
    current_user_id: Optional[int],
    limit: int = 4,
) -> list[SignalRead]:
    clauses = [
        Signal.team_id == team_id,
        Signal.metric_name == metric_name,
    ]
    if player_id is not None:
        clauses.insert(0, Signal.player_id == player_id)
    query = (
        _base_signal_query()
        .where(Signal.id != signal_id)
        .where(or_(*clauses))
        .order_by(Signal.created_at.desc(), Signal.id.desc())
        .limit(limit)
    )
    rows = db.execute(query).all()
    return _build_signal_items(rows, db, current_user_id)
