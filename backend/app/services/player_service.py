from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.signal import Signal
from app.models.team import Team
from app.schemas.player import MetricSeriesPoint, PlayerDetail, PlayerRead
from app.services.signal_service import build_signal_read


def list_players(db: Session) -> list[PlayerRead]:
    rows = db.execute(
        select(Player, Team.name, League.name)
        .join(Team, Player.team_id == Team.id)
        .join(League, Player.league_id == League.id)
        .order_by(League.name, Team.name, Player.name)
    ).all()
    return [
        PlayerRead(
            id=player.id,
            name=player.name,
            position=player.position,
            team_name=team_name,
            league_name=league_name,
        )
        for player, team_name, league_name in rows
    ]


def get_player_detail(db: Session, player_id: int) -> Optional[PlayerDetail]:
    row = db.execute(
        select(Player, Team.name, League.name, func.count(Signal.id))
        .join(Team, Player.team_id == Team.id)
        .join(League, Player.league_id == League.id)
        .outerjoin(Signal, Signal.player_id == Player.id)
        .where(Player.id == player_id)
        .group_by(Player.id, Team.name, League.name)
    ).one_or_none()

    if row is None:
        return None

    player, team_name, league_name, signal_count = row
    return PlayerDetail(
        id=player.id,
        name=player.name,
        position=player.position,
        team_name=team_name,
        league_name=league_name,
        signal_count=signal_count,
    )


def get_player_signals(db: Session, player_id: int):
    rows = db.execute(
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
        .where(Player.id == player_id)
        .order_by(Signal.created_at.desc())
    ).all()
    return [
        build_signal_read(signal, player_name, team_name, league_name, event_date, rolling_stddev)
        for signal, player_name, team_name, league_name, event_date, rolling_stddev in rows
    ]


def get_player_metric_series(db: Session, player_id: int) -> list[MetricSeriesPoint]:
    rows = db.execute(
        select(Game.id, Game.game_date, PlayerGameStat)
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.id)
        .where(PlayerGameStat.player_id == player_id)
        .order_by(Game.game_date)
    ).all()

    points: list[MetricSeriesPoint] = []
    for game_id, game_date, stat in rows:
        metrics = {
            key: float(value)
            for key, value in {
                "points": stat.points,
                "rebounds": stat.rebounds,
                "assists": stat.assists,
                "passing_yards": stat.passing_yards,
                "rushing_yards": stat.rushing_yards,
                "receiving_yards": stat.receiving_yards,
                "touchdowns": stat.touchdowns,
                "usage_rate": stat.usage_rate,
            }.items()
            if value is not None
        }
        points.append(MetricSeriesPoint(game_id=game_id, game_date=game_date, metrics=metrics))
    return points
