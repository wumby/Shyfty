from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.rolling_metric import RollingMetric
from app.models.signal import Signal
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user_follow import UserFollow
from app.schemas.player import PlayerRead
from app.schemas.team import TeamBoxScore, TeamDetail, TeamRead
from app.services.signal_service import EMOJI_TO_LEGACY_REACTION, build_signal_read
from app.services.reaction_service import get_reaction_summaries, get_user_reactions


def list_teams(db: Session, current_user_id: Optional[int] = None) -> list[TeamRead]:
    rows = db.execute(
        select(
            Team.id,
            Team.name,
            League.name,
            func.count(func.distinct(Player.id)),
            func.count(func.distinct(Signal.id)),
        )
        .join(League, Team.league_id == League.id)
        .outerjoin(Player, Player.team_id == Team.id)
        .outerjoin(Signal, Signal.team_id == Team.id)
        .group_by(Team.id, Team.name, League.name)
        .order_by(League.name, Team.name)
    ).all()
    followed_ids = set()
    if current_user_id is not None:
        followed_ids = set(
            db.execute(
                select(UserFollow.entity_id).where(
                    UserFollow.user_id == current_user_id,
                    UserFollow.entity_type == "team",
                )
            ).scalars().all()
        )
    return [
        TeamRead(
            id=team_id,
            name=name,
            league_name=league_name,
            player_count=player_count,
            signal_count=signal_count,
            is_followed=team_id in followed_ids,
        )
        for team_id, name, league_name, player_count, signal_count in rows
    ]


def get_team_detail(
    db: Session,
    team_id: int,
    current_user_id: Optional[int] = None,
) -> Optional[TeamDetail]:
    row = db.execute(
        select(
            Team.id,
            Team.name,
            League.name,
            func.count(func.distinct(Player.id)),
            func.count(func.distinct(Signal.id)),
        )
        .join(League, Team.league_id == League.id)
        .outerjoin(Player, Player.team_id == Team.id)
        .outerjoin(Signal, Signal.team_id == Team.id)
        .where(Team.id == team_id)
        .group_by(Team.id, Team.name, League.name)
    ).one_or_none()

    if row is None:
        return None

    team_db_id, team_name, league_name, player_count, signal_count = row

    player_rows = db.execute(
        select(Player.id, Player.name, Player.position, Team.name, League.name)
        .join(Team, Player.team_id == Team.id)
        .join(League, Player.league_id == League.id)
        .where(Player.team_id == team_id)
        .order_by(Player.name)
    ).all()

    players = [
        PlayerRead(id=pid, name=pname, position=position, team_name=tname, league_name=lname)
        for pid, pname, position, tname, lname in player_rows
    ]

    signal_rows = db.execute(
        select(Signal, Player.name, Team.name, League.name, Game.game_date, RollingMetric, TeamGameStat.opponent_name, TeamGameStat.home_away)
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
        .outerjoin(TeamGameStat, TeamGameStat.id == Signal.source_team_stat_id)
        .where(Signal.team_id == team_id)
        .order_by(Signal.created_at.desc())
        .limit(20)
    ).all()

    signal_ids = [sig.id for sig, *_ in signal_rows]
    reaction_summaries = get_reaction_summaries(db, signal_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, signal_ids=signal_ids)

    recent_signals = [
        # Keep legacy user_reaction compatible while also returning user_reactions.
        build_signal_read(
            sig, pname, tname, lname, event_date, rolling_metric,
            reactions=reaction_summaries.get(sig.id),
            user_reactions=sorted(user_reactions.get(sig.id, set())),
            user_reaction=EMOJI_TO_LEGACY_REACTION.get(
                next(iter(user_reactions.get(sig.id, set())), ""),
                next(iter(user_reactions.get(sig.id, set())), None),
            ),
            opponent=opponent_name,
            home_away=home_away,
        )
        for sig, pname, tname, lname, event_date, rolling_metric, opponent_name, home_away in signal_rows
    ]

    return TeamDetail(
        id=team_db_id,
        name=team_name,
        league_name=league_name,
        player_count=player_count,
        signal_count=signal_count,
        is_followed=(
            current_user_id is not None and db.execute(
                select(UserFollow.id).where(
                    UserFollow.user_id == current_user_id,
                    UserFollow.entity_type == "team",
                    UserFollow.entity_id == team_db_id,
                )
            ).scalar_one_or_none() is not None
        ),
        players=players,
        recent_signals=recent_signals,
        recent_box_scores=get_team_box_scores(db, team_id=team_db_id, limit=5),
    )


def get_team_box_scores(db: Session, team_id: int, limit: int = 5) -> list[TeamBoxScore]:
    rows = db.execute(
        select(Game.id, Game.game_date, Game.season, TeamGameStat)
        .join(TeamGameStat, TeamGameStat.game_id == Game.id)
        .where(TeamGameStat.team_id == team_id)
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(limit)
    ).all()

    return [
        TeamBoxScore(
            game_id=game_id,
            game_date=game_date,
            season=season,
            opponent=stat.opponent_name or "Opponent",
            home_away=stat.home_away or "",
            points=stat.points,
            rebounds=stat.rebounds,
            assists=stat.assists,
            fg_pct=stat.fg_pct,
            fg3_pct=stat.fg3_pct,
            turnovers=stat.turnovers,
            pace=stat.pace,
            off_rating=stat.off_rating,
            total_yards=stat.total_yards,
            first_downs=stat.first_downs,
            penalties=stat.penalties,
            penalty_yards=stat.penalty_yards,
            turnovers_forced=stat.turnovers_forced,
            turnovers_lost=stat.turnovers_lost,
            third_down_pct=stat.third_down_pct,
            redzone_pct=stat.redzone_pct,
        )
        for game_id, game_date, season, stat in rows
    ]
