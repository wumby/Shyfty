from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.rolling_metric import RollingMetric
from app.models.shyft import Shyft
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user_follow import UserFollow
from app.schemas.player import PlayerRead
from app.schemas.team import TeamBoxScore, TeamDetail, TeamRead
from app.services.shyft_service import _comment_count_subquery, build_shyft_read
from app.services.reaction_service import get_reaction_summaries, get_user_reactions


def list_teams(db: Session, current_user_id: Optional[int] = None) -> list[TeamRead]:
    rows = db.execute(
        select(
            Team.id,
            Team.name,
            League.name,
            func.count(func.distinct(Player.id)),
            func.count(func.distinct(Shyft.id)),
        )
        .join(League, Team.league_id == League.id)
        .outerjoin(Player, Player.team_id == Team.id)
        .outerjoin(Shyft, Shyft.team_id == Team.id)
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
            shyft_count=shyft_count,
            is_followed=team_id in followed_ids,
        )
        for team_id, name, league_name, player_count, shyft_count in rows
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
            func.count(func.distinct(Shyft.id)),
        )
        .join(League, Team.league_id == League.id)
        .outerjoin(Player, Player.team_id == Team.id)
        .outerjoin(Shyft, Shyft.team_id == Team.id)
        .where(Team.id == team_id)
        .group_by(Team.id, Team.name, League.name)
    ).one_or_none()

    if row is None:
        return None

    team_db_id, team_name, league_name, player_count, shyft_count = row

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

    comment_count_subq = _comment_count_subquery()
    shyft_rows = db.execute(
        select(
            Shyft, Player.name, Team.name, League.name, Game.game_date, RollingMetric,
            TeamGameStat.opponent_name, TeamGameStat.home_away,
            func.coalesce(comment_count_subq.c.comment_count, 0).label("comment_count"),
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
        .outerjoin(TeamGameStat, TeamGameStat.id == Shyft.source_team_stat_id)
        .outerjoin(comment_count_subq, comment_count_subq.c.shyft_id == Shyft.id)
        .where(Shyft.team_id == team_id)
        .order_by(Shyft.created_at.desc())
        .limit(20)
    ).all()

    shyft_ids = [sig.id for sig, *_ in shyft_rows]
    reaction_summaries = get_reaction_summaries(db, shyft_ids)
    user_reactions = get_user_reactions(db, user_id=current_user_id, shyft_ids=shyft_ids)

    recent_shyfts = [
        build_shyft_read(
            sig, pname, tname, lname, event_date, rolling_metric,
            reactions=reaction_summaries.get(sig.id),
            user_reactions=sorted(user_reactions.get(sig.id, set())),
            user_reaction=next(iter(user_reactions.get(sig.id, set())), None),
            opponent=opponent_name,
            home_away=home_away,
            comment_count=comment_count,
        )
        for sig, pname, tname, lname, event_date, rolling_metric, opponent_name, home_away, comment_count in shyft_rows
    ]

    return TeamDetail(
        id=team_db_id,
        name=team_name,
        league_name=league_name,
        player_count=player_count,
        shyft_count=shyft_count,
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
        recent_shyfts=recent_shyfts,
        recent_box_scores=get_team_box_scores(db, team_id=team_db_id, limit=5),
    )


def get_team_box_scores(db: Session, team_id: int, limit: int = 5) -> list[TeamBoxScore]:
    opponent_stat = aliased(TeamGameStat)
    rows = db.execute(
        select(Game.id, Game.game_date, Game.season, TeamGameStat, opponent_stat.points)
        .join(TeamGameStat, TeamGameStat.game_id == Game.id)
        .outerjoin(
            opponent_stat,
            and_(
                opponent_stat.game_id == TeamGameStat.game_id,
                opponent_stat.team_id != TeamGameStat.team_id,
            ),
        )
        .where(TeamGameStat.team_id == team_id)
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(limit)
    ).all()

    result: list[TeamBoxScore] = []
    for game_id, game_date, season, stat, opponent_points in rows:
        team_points = stat.points
        game_result = None
        if team_points is not None and opponent_points is not None:
            if team_points > opponent_points:
                game_result = "W"
            elif team_points < opponent_points:
                game_result = "L"
            else:
                game_result = "T"

        result.append(
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
                team_score=team_points,
                opponent_score=opponent_points,
                result=game_result,
            )
        )
    return result
