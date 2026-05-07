from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Optional

from sqlalchemy import and_, case, func, literal, or_, select
from sqlalchemy.orm import Session, aliased

from app.domain.shyfts import (
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
    stat_shyft_config,
    performance_ratio,
    shyft_gate_trace,
    trend_direction,
)
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.shyft import Shyft
from app.models.shyft_comment import ShyftComment
from app.models.shyft_reaction import ShyftReactionRecord
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user_follow import UserFollow
from app.schemas.reaction import ReactionAggregateRead, ReactionSummaryRead, ShyftReaction
from app.schemas.shyft import (
    CascadeContributorRead,
    CascadePlayerRead,
    CascadeShyftRead,
    CascadeTriggerRead,
    FeedContextRead,
    FeedItemRead,
    PaginatedShyfts,
    ShyftDebugTraceRead,
    ShyftRead,
    ShyftSummaryTemplateInputs,
)
from app.services.reaction_service import get_reaction_summaries, get_user_reactions

SORT_MODE_NEWEST = "newest"
SORT_MODE_IMPORTANT = "most_important"
SORT_MODE_DEVIATION = "biggest_deviation"
SORT_MODE_DISCUSSED = "most_discussed"

FEED_MODE_ALL = "all"
FEED_MODE_FOLLOWING = "following"
FEED_MODE_FOR_YOU = "for_you"
EXCLUDED_SHYFT_TYPES = {"CONSISTENCY"}
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
    return func.abs(Shyft.current_value - Shyft.baseline_value)


def _severity_order_expr():
    return case(
        (Shyft.shyft_type == "OUTLIER", 3),
        (Shyft.shyft_type == "SWING", 2),
        (Shyft.shyft_type == "SHIFT", 1),
        else_=0,
    )


def _severity_filter_expr(shyft_type: str):
    return Shyft.shyft_type.ilike(shyft_type)


def effective_metric_to_snapshot(shyft: Shyft, rolling_metric: Optional[RollingMetric]) -> MetricSnapshot:
    short_values = rolling_metric.short_values if rolling_metric and rolling_metric.short_values else [shyft.baseline_value]
    medium_values = rolling_metric.medium_values if rolling_metric and rolling_metric.medium_values else short_values
    season_values = rolling_metric.season_values if rolling_metric and rolling_metric.season_values else medium_values
    return MetricSnapshot(
        game_id=shyft.game_id,
        source_stat_id=shyft.source_stat_id or 0,
        event_date=None,
        baseline_stat_ids=[],
        current_value=shyft.current_value,
        baseline_value=shyft.baseline_value,
        rolling_stddev=rolling_metric.short_rolling_stddev if rolling_metric and rolling_metric.short_rolling_stddev is not None else 0.0,
        z_score=shyft.z_score,
        short_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in short_values],
            rolling_avg=rolling_metric.short_rolling_avg if rolling_metric and rolling_metric.short_rolling_avg is not None else shyft.baseline_value,
            rolling_stddev=rolling_metric.short_rolling_stddev if rolling_metric and rolling_metric.short_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.short_z_score if rolling_metric and rolling_metric.short_z_score is not None else shyft.z_score,
        ),
        medium_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in medium_values],
            rolling_avg=rolling_metric.medium_rolling_avg if rolling_metric and rolling_metric.medium_rolling_avg is not None else shyft.baseline_value,
            rolling_stddev=rolling_metric.medium_rolling_stddev if rolling_metric and rolling_metric.medium_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.medium_z_score if rolling_metric and rolling_metric.medium_z_score is not None else shyft.z_score,
        ),
        season_window=WindowSnapshot(
            stat_ids=[],
            values=[float(value) for value in season_values],
            rolling_avg=rolling_metric.season_rolling_avg if rolling_metric and rolling_metric.season_rolling_avg is not None else shyft.baseline_value,
            rolling_stddev=rolling_metric.season_rolling_stddev if rolling_metric and rolling_metric.season_rolling_stddev is not None else 0.0,
            z_score=rolling_metric.season_z_score if rolling_metric and rolling_metric.season_z_score is not None else shyft.z_score,
        ),
        ewma=rolling_metric.ewma if rolling_metric and rolling_metric.ewma is not None else shyft.baseline_value,
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


def build_shyft_read(
    shyft: Shyft,
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
) -> ShyftRead:
    baseline_window = baseline_window_label()
    movement = meaningful_movement_pct(shyft.metric_name, shyft.current_value, shyft.baseline_value)
    performance = performance_ratio(shyft.current_value, shyft.baseline_value)
    deviation = deviation_from_expected(shyft.current_value, shyft.baseline_value)
    severity = shyft.shyft_type
    direction = trend_direction(shyft.current_value, shyft.baseline_value)
    readable_metric_label = metric_label(shyft.metric_name)
    snapshot = effective_metric_to_snapshot(shyft, rolling_metric)
    debug_trace = shyft_gate_trace(snapshot, shyft.metric_name)
    shyft_score = round(shyft.shyft_score or importance_score(severity, shyft.z_score, deviation), 1)
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

    return ShyftRead(
        id=shyft.id,
        subject_type=shyft.subject_type,
        player_id=shyft.player_id,
        team_id=shyft.team_id,
        game_id=shyft.game_id,
        player_name=player_name or team_name,
        team_name=team_name,
        league_name=league_name,
        shyft_type=severity,
        severity=severity,
        metric_name=shyft.metric_name,
        current_value=shyft.current_value,
        baseline_value=shyft.baseline_value,
        performance=performance,
        deviation=deviation,
        z_score=shyft.z_score,
        shyft_score=shyft_score,
        score_explanation=shyft.score_explanation,
        explanation=shyft.explanation,
        importance=shyft_score,
        importance_label=importance_label_for_score(shyft_score),
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
        classification_reason=classification_reason(severity, snapshot, shyft.metric_name),
        debug_trace=ShyftDebugTraceRead(**debug_trace),
        summary_template="metric_vs_recent_baseline",
        summary_template_inputs=ShyftSummaryTemplateInputs(
            current_value=shyft.current_value,
            baseline_value=shyft.baseline_value,
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
        created_at=shyft.created_at,
    )


def _comment_count_subquery():
    base_shyft = aliased(Shyft)
    comment_shyft = aliased(Shyft)
    same_shyft_group = and_(
        comment_shyft.game_id == base_shyft.game_id,
        comment_shyft.subject_type == base_shyft.subject_type,
        or_(
            and_(base_shyft.player_id.is_not(None), comment_shyft.player_id == base_shyft.player_id),
            and_(
                base_shyft.player_id.is_(None),
                comment_shyft.player_id.is_(None),
                comment_shyft.team_id == base_shyft.team_id,
            ),
        ),
    )
    return (
        select(base_shyft.id.label("shyft_id"), func.count(ShyftComment.id).label("comment_count"))
        .select_from(base_shyft)
        .outerjoin(comment_shyft, same_shyft_group)
        .outerjoin(ShyftComment, ShyftComment.shyft_id == comment_shyft.id)
        .group_by(base_shyft.id)
        .subquery()
    )


def _reaction_count_subquery():
    return (
        select(ShyftReactionRecord.shyft_id, func.count(ShyftReactionRecord.id).label("reaction_count"))
        .group_by(ShyftReactionRecord.shyft_id)
        .subquery()
    )


def _base_shyft_query():
    reaction_count_subq = _reaction_count_subquery()
    home_team = aliased(Team)
    away_team = aliased(Team)
    shyft_team_stat = aliased(TeamGameStat)
    opponent_team_stat = aliased(TeamGameStat)
    return (
        select(
            Shyft,
            Player.name,
            Team.name,
            League.name,
            Game.game_date,
            RollingMetric,
            literal(0).label("comment_count"),
            func.coalesce(reaction_count_subq.c.reaction_count, 0).label("reaction_count"),
            PlayerGameStat.plus_minus,
            Game.home_team_id,
            Game.away_team_id,
            home_team.name.label("home_team_name"),
            away_team.name.label("away_team_name"),
            TeamGameStat.opponent_name,
            TeamGameStat.home_away,
            shyft_team_stat.points.label("shyft_team_points"),
            opponent_team_stat.points.label("opponent_team_points"),
        )
        .outerjoin(Player, Shyft.player_id == Player.id)
        .join(Team, Shyft.team_id == Team.id)
        .join(League, Shyft.league_id == League.id)
        .join(Game, Shyft.game_id == Game.id)
        .outerjoin(
            RollingMetric,
            and_(
                RollingMetric.player_id == Shyft.player_id,
                RollingMetric.game_id == Shyft.game_id,
                RollingMetric.metric_name == Shyft.metric_name,
            ),
        )
        .outerjoin(PlayerGameStat, PlayerGameStat.id == Shyft.source_stat_id)
        .outerjoin(TeamGameStat, TeamGameStat.id == Shyft.source_team_stat_id)
        .outerjoin(
            shyft_team_stat,
            and_(shyft_team_stat.game_id == Shyft.game_id, shyft_team_stat.team_id == Shyft.team_id),
        )
        .outerjoin(
            opponent_team_stat,
            and_(opponent_team_stat.game_id == Shyft.game_id, opponent_team_stat.team_id != Shyft.team_id),
        )
        .outerjoin(home_team, Game.home_team_id == home_team.id)
        .outerjoin(away_team, Game.away_team_id == away_team.id)
        .outerjoin(reaction_count_subq, reaction_count_subq.c.shyft_id == Shyft.id)
        .where(~Shyft.shyft_type.in_(EXCLUDED_SHYFT_TYPES))
    )


def _group_key(shyft: Shyft) -> tuple[str, int, Optional[int], Optional[int]]:
    if shyft.player_id is not None:
        return (shyft.subject_type, shyft.game_id, shyft.player_id, None)
    return (shyft.subject_type, shyft.game_id, None, shyft.team_id)


def _comment_counts_for_selected_groups(db: Session, shyfts: list[Shyft]) -> dict[int, int]:
    if not shyfts:
        return {}

    clauses = []
    for shyft in shyfts:
        base = [
            Shyft.game_id == shyft.game_id,
            Shyft.subject_type == shyft.subject_type,
        ]
        if shyft.player_id is not None:
            base.append(Shyft.player_id == shyft.player_id)
        else:
            base.extend([Shyft.player_id.is_(None), Shyft.team_id == shyft.team_id])
        clauses.append(and_(*base))

    rows = db.execute(
        select(
            Shyft.id,
            Shyft.subject_type,
            Shyft.game_id,
            Shyft.player_id,
            Shyft.team_id,
            func.count(ShyftComment.id),
        )
        .outerjoin(ShyftComment, ShyftComment.shyft_id == Shyft.id)
        .where(or_(*clauses))
        .group_by(Shyft.id, Shyft.subject_type, Shyft.game_id, Shyft.player_id, Shyft.team_id)
    ).all()

    group_counts: dict[tuple[str, int, Optional[int], Optional[int]], int] = defaultdict(int)
    for _id, subject_type, game_id, player_id, team_id, count in rows:
        key = (subject_type, game_id, player_id if player_id is not None else None, None if player_id is not None else team_id)
        group_counts[key] += int(count)

    return {shyft.id: group_counts.get(_group_key(shyft), 0) for shyft in shyfts}


def _get_engagement_context(db: Session, user_id: int) -> dict[str, object]:
    followed_rows = db.execute(
        select(UserFollow.entity_type, UserFollow.entity_id).where(UserFollow.user_id == user_id)
    ).all()
    followed_players = {entity_id for entity_type, entity_id in followed_rows if entity_type == "player"}
    followed_teams = {entity_id for entity_type, entity_id in followed_rows if entity_type == "team"}

    reaction_rows = db.execute(
        select(Shyft.player_id, Shyft.team_id, Shyft.metric_name)
        .join(ShyftReactionRecord, ShyftReactionRecord.shyft_id == Shyft.id)
        .where(ShyftReactionRecord.user_id == user_id)
    ).all()
    comment_rows = db.execute(
        select(Shyft.player_id, Shyft.team_id, Shyft.metric_name)
        .join(ShyftComment, ShyftComment.shyft_id == Shyft.id)
        .where(ShyftComment.user_id == user_id)
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
        func.coalesce(Shyft.shyft_score, 0).desc(),
        _severity_order_expr().desc(),
        deviation_expr.desc(),
        Game.game_date.desc(),
        Shyft.id.desc(),
    )
    if sort_mode == SORT_MODE_IMPORTANT:
        return query.order_by(*ranked_order)
    if sort_mode == SORT_MODE_DEVIATION:
        return query.order_by(*ranked_order)
    return query.order_by(Game.game_date.desc(), Shyft.id.desc())


def _compute_streaks(
    db: Session,
    shyft_info: list[tuple[int, Optional[int], str, str, date]],
) -> dict[int, int]:
    """
    shyft_info: [(shyft_id, player_id, metric_name, shyft_type, event_date), ...]
    Returns {shyft_id: streak_count}.
    Streak = consecutive prior games (by date, going back) where the same player
    had the same shyft_type for the same metric, with no gap of a different type.
    """
    player_metric_pairs = {
        (pid, metric)
        for _, pid, metric, _, _ in shyft_info
        if pid is not None
    }
    if not player_metric_pairs:
        return {sig_id: 1 for sig_id, *_ in shyft_info}

    history_rows = db.execute(
        select(Shyft.player_id, Shyft.metric_name, Shyft.shyft_type, Game.game_date)
        .join(Game, Shyft.game_id == Game.id)
        .where(~Shyft.shyft_type.in_(EXCLUDED_SHYFT_TYPES))
        .where(or_(*[
            and_(Shyft.player_id == pid, Shyft.metric_name == metric)
            for pid, metric in player_metric_pairs
        ]))
        .order_by(Game.game_date.desc(), Shyft.id.desc())
    ).all()

    history: dict[tuple, list[tuple[str, date]]] = defaultdict(list)
    for player_id, metric_name, sig_type, game_date in history_rows:
        history[(player_id, metric_name)].append((sig_type, game_date))

    result: dict[int, int] = {}
    for sig_id, player_id, metric_name, shyft_type, event_date in shyft_info:
        if player_id is None:
            result[sig_id] = 1
            continue
        relevant = [(st, gd) for st, gd in history[(player_id, metric_name)] if gd <= event_date]
        count = 0
        for st, _ in relevant:
            if st == shyft_type:
                count += 1
            else:
                break
        result[sig_id] = max(count, 1)

    return result


def _build_shyft_items(rows, db: Session, current_user_id: Optional[int]) -> list[ShyftRead]:
    shyft_ids = [shyft.id for shyft, *_ in rows]
    group_comment_counts = _comment_counts_for_selected_groups(db, [shyft for shyft, *_ in rows])
    reaction_summaries = get_reaction_summaries(db, shyft_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, shyft_ids=shyft_ids)

    shyft_info = [
        (shyft.id, shyft.player_id, shyft.metric_name, shyft.shyft_type, event_date)
        for shyft, _player_name, _team_name, _league_name, event_date, *_ in rows
    ]
    streaks = _compute_streaks(db, shyft_info)

    items: list[ShyftRead] = []
    for (
        shyft,
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
        shyft_team_points,
        opponent_team_points,
    ) in rows:
        is_home = shyft.team_id == home_team_id
        opponent = team_stat_opponent_name or (away_team_name if is_home else home_team_name)
        home_away = team_stat_home_away or ("vs" if is_home else "@")
        final_score = (
            f"{int(shyft_team_points)}-{int(opponent_team_points)}"
            if shyft_team_points is not None and opponent_team_points is not None
            else None
        )
        score_result = (
            "W"
            if shyft_team_points is not None and opponent_team_points is not None and shyft_team_points > opponent_team_points
            else "L"
            if shyft_team_points is not None and opponent_team_points is not None and shyft_team_points < opponent_team_points
            else None
        )
        game_result = score_result or (None if shyft.subject_type == "team" else ("W" if plus_minus and plus_minus > 0 else "L" if plus_minus and plus_minus < 0 else None))

        current_user_reactions = sorted(user_reactions.get(shyft.id, set()))
        items.append(
            build_shyft_read(
                shyft,
                player_name,
                team_name,
                league_name,
                event_date,
                rolling_metric,
                reactions=reaction_summaries.get(shyft.id),
                user_reactions=current_user_reactions,
                user_reaction=next(iter(user_reactions.get(shyft.id, set())), None),
                comment_count=group_comment_counts.get(shyft.id, comment_count),
                opponent=opponent,
                home_away=home_away,
                game_result=game_result,
                final_score=final_score,
                streak=streaks.get(shyft.id, 1),
            )
        )
    return items


def _delta_percent(item: ShyftRead) -> Optional[float]:
    if item.movement_pct is not None:
        return item.movement_pct
    if abs(item.baseline_value) < 0.05:
        return None
    return ((item.current_value - item.baseline_value) / item.baseline_value) * 100


def _is_cascade_trigger(item: ShyftRead) -> bool:
    if item.subject_type != "player" or item.player_id is None:
        return False
    if item.metric_name not in CASCADE_TRIGGER_STATS:
        return False
    if item.current_value >= item.baseline_value:
        return False
    drop_pct = _delta_percent(item)
    return item.current_value <= 0.5 or (drop_pct is not None and drop_pct <= CASCADE_MIN_TRIGGER_DROP_PCT)


def _is_cascade_contributor(item: ShyftRead, trigger: ShyftRead) -> bool:
    if item.subject_type != "player" or item.player_id is None:
        return False
    if item.game_id != trigger.game_id or item.team_id != trigger.team_id or item.player_id == trigger.player_id:
        return False
    if item.metric_name not in CASCADE_ALLOWED_CONTRIBUTOR_STATS:
        return False
    if item.current_value <= item.baseline_value:
        return False
    config = stat_shyft_config(item.metric_name)
    if item.current_value - item.baseline_value < config.min_delta:
        return False
    return item.shyft_score >= CASCADE_MIN_CONTRIBUTOR_SCORE


def _cascade_rank_key(item: ShyftRead) -> tuple[float, float, float]:
    delta_pct = _delta_percent(item)
    return (
        item.shyft_score,
        abs(delta_pct) if delta_pct is not None else 0.0,
        abs(item.z_score),
    )


def _trigger_read(item: ShyftRead) -> CascadeTriggerRead:
    return CascadeTriggerRead(
        player=CascadePlayerRead(id=item.player_id, name=item.player_name),
        shyft_id=item.id,
        stat=item.metric_name,
        metric_label=item.metric_label,
        delta=item.current_value - item.baseline_value,
        delta_percent=_delta_percent(item),
        shyft_type=item.shyft_type,
        shyft_score=item.shyft_score,
    )


def _contributor_read(item: ShyftRead) -> CascadeContributorRead:
    return CascadeContributorRead(
        player=CascadePlayerRead(id=item.player_id, name=item.player_name),
        shyft_id=item.id,
        stat=item.metric_name,
        metric_label=item.metric_label,
        delta=item.current_value - item.baseline_value,
        delta_percent=_delta_percent(item),
        shyft_type=item.shyft_type,
        shyft_score=item.shyft_score,
    )


def _cascade_drop_reason(trigger: ShyftRead) -> str:
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


def _cascade_summary(trigger: ShyftRead, contributors: list[ShyftRead]) -> str:
    primary = contributors[0]
    reason = _cascade_drop_reason(trigger)
    primary_phrase = _cascade_usage_phrase(primary.metric_name)
    summary = f"{trigger.player_name} {reason} → {primary.player_name} absorbed primary {primary_phrase}"
    if len(contributors) >= 2:
        secondary = contributors[1]
        secondary_phrase = _cascade_usage_phrase(secondary.metric_name)
        summary += f", {secondary.player_name} secondary {secondary_phrase}"
    return f"{summary}."


def detect_cascade_shyfts(items: list[ShyftRead], *, max_contributors: int = CASCADE_MAX_CONTRIBUTORS) -> list[CascadeShyftRead]:
    cascades: list[CascadeShyftRead] = []
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
            CascadeShyftRead(
                id=f"cascade:{trigger.game_id}:{trigger.team_id}:{trigger.player_id}",
                game_id=trigger.game_id,
                team_id=trigger.team_id,
                team=trigger.team_name,
                league_name=trigger.league_name,
                game_date=trigger.event_date,
                created_at=max([trigger.created_at, *[contributor.created_at for contributor in kept]]),
                trigger=_trigger_read(trigger),
                contributors=[_contributor_read(contributor) for contributor in kept],
                underlying_shyfts=[trigger, *kept],
                narrative_summary=_cascade_summary(trigger, kept),
            )
        )

    return cascades


def _inject_cascades(items: list[ShyftRead]) -> list[FeedItemRead]:
    cascades = detect_cascade_shyfts(items)
    if not cascades:
        return items

    cascades_by_trigger_id = {cascade.trigger.shyft_id: cascade for cascade in cascades}
    grouped_shyft_ids = {
        shyft.id
        for cascade in cascades
        for shyft in cascade.underlying_shyfts
    }

    feed_items: list[FeedItemRead] = []
    for item in items:
        cascade = cascades_by_trigger_id.get(item.id)
        if cascade is not None:
            feed_items.append(cascade)
            continue
        if item.id in grouped_shyft_ids:
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
        return "This view will fill in as you follow players or teams and react to shyfts."
    if feed_mode == FEED_MODE_FOLLOWING:
        return "Shyfts from players and teams you follow."
    if feed_mode == FEED_MODE_FOR_YOU:
        return "Ranked from your follows, comments, and reaction history."
    return None


def list_shyfts(
    db: Session,
    league: Optional[str],
    team: Optional[str],
    player: Optional[str],
    shyft_type: Optional[str],
    limit: int = 24,
    before_id: Optional[int] = None,
    current_user_id: Optional[int] = None,
    sort_mode: str = SORT_MODE_NEWEST,
    feed_mode: str = FEED_MODE_ALL,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> PaginatedShyfts:
    limit = max(1, min(limit, 50))
    query = _base_shyft_query()

    if league:
        query = query.where(League.name.ilike(league))
    if team:
        query = query.where(Team.name.ilike(f"%{team}%"))
    if player:
        query = query.where(Player.name.ilike(f"%{player}%"))
    if shyft_type:
        query = query.where(_severity_filter_expr(shyft_type))
    if date_from is not None:
        query = query.where(Game.game_date >= date_from)
    if date_to is not None:
        query = query.where(Game.game_date <= date_to)
    if before_id is not None and sort_mode == SORT_MODE_NEWEST and feed_mode == FEED_MODE_ALL:
        query = query.where(Shyft.id < before_id)

    if feed_mode == FEED_MODE_FOLLOWING:
        if current_user_id is None:
            return PaginatedShyfts(
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
            return PaginatedShyfts(
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
            follow_clauses.append(and_(Shyft.subject_type == "player", Shyft.player_id.in_(followed_players)))
        if followed_teams:
            follow_clauses.append(and_(Shyft.subject_type == "team", Shyft.team_id.in_(followed_teams)))
        query = query.where(or_(*follow_clauses))

    elif feed_mode == FEED_MODE_FOR_YOU and current_user_id is not None:
        query = query.limit(max(limit * 5, 120))
        rows = db.execute(_apply_sort(query, SORT_MODE_NEWEST)).all()
        items = _build_shyft_items(rows, db, current_user_id)
        preferred = _get_engagement_context(db, current_user_id)

        def score(item: ShyftRead) -> float:
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
        return PaginatedShyfts(
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
    items = _build_shyft_items(rows, db, current_user_id)
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
    shyft_cursor_items = [item for item in feed_items if isinstance(item, ShyftRead)]
    next_cursor = shyft_cursor_items[-1].id if has_more and shyft_cursor_items else (items[-1].id if has_more and items else None)

    return PaginatedShyfts(
        items=feed_items,
        has_more=has_more,
        next_cursor=next_cursor,
        feed_context=FeedContextRead(
            feed_mode=feed_mode,
            sort_mode=sort_mode,
            personalization_reason=_personalized_reason(feed_mode, current_user_id, feed_items),
        ),
    )


def list_trending_shyfts(
    db: Session,
    limit: int = 12,
    current_user_id: Optional[int] = None,
) -> list[ShyftRead]:
    limit = max(1, min(limit, 50))
    page = list_shyfts(
        db=db,
        league=None,
        team=None,
        player=None,
        shyft_type=None,
        limit=limit,
        before_id=None,
        current_user_id=current_user_id,
        sort_mode=SORT_MODE_IMPORTANT,
    )
    return page.items
