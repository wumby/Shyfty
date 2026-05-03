from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, aliased

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.signal import Signal
from app.models.team import Team
from app.models.user_follow import UserFollow
from app.schemas.player import GameLogRow, MetricSeriesPoint, PlayerBoxScore, PlayerDetail, PlayerRead, SeasonAveragesRow
from app.services.signal_service import _comment_count_subquery, build_signal_read


def list_players(db: Session, current_user_id: Optional[int] = None) -> list[PlayerRead]:
    rows = db.execute(
        select(Player, Team.name, League.name)
        .join(Team, Player.team_id == Team.id)
        .join(League, Player.league_id == League.id)
        .order_by(League.name, Team.name, Player.name)
    ).all()
    followed_ids = set()
    if current_user_id is not None:
        followed_ids = set(
            db.execute(
                select(UserFollow.entity_id).where(
                    UserFollow.user_id == current_user_id,
                    UserFollow.entity_type == "player",
                )
            ).scalars().all()
        )
    return [
        PlayerRead(
            id=player.id,
            name=player.name,
            position=player.position,
            team_name=team_name,
            league_name=league_name,
            is_followed=player.id in followed_ids,
        )
        for player, team_name, league_name in rows
    ]


def get_player_detail(db: Session, player_id: int, current_user_id: Optional[int] = None) -> Optional[PlayerDetail]:
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
        recent_box_scores=get_player_box_scores(db, player_id, limit=5),
        is_followed=(
            current_user_id is not None and db.execute(
                select(UserFollow.id).where(
                    UserFollow.user_id == current_user_id,
                    UserFollow.entity_type == "player",
                    UserFollow.entity_id == player.id,
                )
            ).scalar_one_or_none() is not None
        ),
    )


def get_player_box_scores(db: Session, player_id: int, limit: int = 5) -> list[PlayerBoxScore]:
    HomeTeam = aliased(Team)
    AwayTeam = aliased(Team)

    rows = db.execute(
        select(
            Game.id,
            Game.game_date,
            Game.season,
            Game.home_team_id,
            Game.away_team_id,
            HomeTeam.name,
            AwayTeam.name,
            Player.team_id,
            PlayerGameStat,
        )
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.id)
        .join(Player, Player.id == PlayerGameStat.player_id)
        .join(HomeTeam, Game.home_team_id == HomeTeam.id)
        .join(AwayTeam, Game.away_team_id == AwayTeam.id)
        .where(PlayerGameStat.player_id == player_id)
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(limit)
    ).all()

    box_scores: list[PlayerBoxScore] = []
    for game_id, game_date, game_season, home_team_id, _away_team_id, home_name, away_name, player_team_id, stat in rows:
        is_home = player_team_id == home_team_id
        box_scores.append(PlayerBoxScore(
            game_id=game_id,
            game_date=game_date,
            season=game_season,
            opponent=away_name if is_home else home_name,
            home_away="Home" if is_home else "Away",
            points=stat.points,
            rebounds=stat.rebounds,
            assists=stat.assists,
            passing_yards=stat.passing_yards,
            passing_completions=stat.passing_completions,
            passing_attempts=stat.passing_attempts,
            interceptions=stat.interceptions,
            rushing_yards=stat.rushing_yards,
            rushing_attempts=stat.rushing_attempts,
            receiving_yards=stat.receiving_yards,
            receptions=stat.receptions,
            targets=stat.targets,
            touchdowns=stat.touchdowns,
            sacks=stat.sacks,
            fumbles_lost=stat.fumbles_lost,
            usage_rate=stat.usage_rate,
            steals=stat.steals,
            blocks=stat.blocks,
            turnovers=stat.turnovers,
            minutes_played=stat.minutes_played,
            plus_minus=stat.plus_minus,
            fg_pct=stat.fg_pct,
            fg3_pct=stat.fg3_pct,
            ft_pct=stat.ft_pct,
        ))
    return box_scores


def get_player_signals(db: Session, player_id: int):
    comment_count_subq = _comment_count_subquery()
    rows = db.execute(
        select(
            Signal, Player.name, Team.name, League.name, Game.game_date, RollingMetric,
            func.coalesce(comment_count_subq.c.comment_count, 0).label("comment_count"),
        )
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
        .outerjoin(comment_count_subq, comment_count_subq.c.signal_id == Signal.id)
        .where(Player.id == player_id)
        .order_by(Signal.created_at.desc())
    ).all()
    return [
        build_signal_read(signal, player_name, team_name, league_name, event_date, rolling_metric,
                          comment_count=comment_count)
        for signal, player_name, team_name, league_name, event_date, rolling_metric, comment_count in rows
    ]


def get_player_gamelog(db: Session, player_id: int, season: Optional[str] = None) -> list[GameLogRow]:
    HomeTeam = aliased(Team)
    AwayTeam = aliased(Team)

    query = (
        select(
            Game.id,
            Game.game_date,
            Game.season,
            Game.home_team_id,
            Game.away_team_id,
            HomeTeam.name,
            AwayTeam.name,
            Player.team_id,
            PlayerGameStat,
        )
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.id)
        .join(Player, Player.id == PlayerGameStat.player_id)
        .join(HomeTeam, Game.home_team_id == HomeTeam.id)
        .join(AwayTeam, Game.away_team_id == AwayTeam.id)
        .where(PlayerGameStat.player_id == player_id)
    )
    if season:
        query = query.where(Game.season == season)
    query = query.order_by(Game.game_date.desc())

    rows = db.execute(query).all()

    result = []
    for game_id, game_date, game_season, home_team_id, away_team_id, home_name, away_name, player_team_id, stat in rows:
        is_home = player_team_id == home_team_id
        result.append(GameLogRow(
            game_id=game_id,
            game_date=game_date,
            season=game_season,
            opponent=away_name if is_home else home_name,
            home_away="Home" if is_home else "Away",
            points=stat.points,
            rebounds=stat.rebounds,
            assists=stat.assists,
            passing_yards=stat.passing_yards,
            passing_completions=stat.passing_completions,
            passing_attempts=stat.passing_attempts,
            interceptions=stat.interceptions,
            rushing_yards=stat.rushing_yards,
            rushing_attempts=stat.rushing_attempts,
            receiving_yards=stat.receiving_yards,
            receptions=stat.receptions,
            targets=stat.targets,
            touchdowns=stat.touchdowns,
            sacks=stat.sacks,
            fumbles_lost=stat.fumbles_lost,
            usage_rate=stat.usage_rate,
        ))
    return result


def get_player_season_averages(db: Session, player_id: int) -> list[SeasonAveragesRow]:
    rows = db.execute(
        select(Game.season, PlayerGameStat)
        .join(PlayerGameStat, PlayerGameStat.game_id == Game.id)
        .where(PlayerGameStat.player_id == player_id)
        .where(Game.season.isnot(None))
        .order_by(Game.season.desc(), Game.game_date.desc())
    ).all()

    by_season: dict[str, list] = {}
    for season, stat in rows:
        by_season.setdefault(season, []).append(stat)

    def _avg(stats, attr):
        vals = [getattr(s, attr) for s in stats if getattr(s, attr) is not None]
        return round(sum(vals) / len(vals), 1) if vals else None

    result = []
    for season in sorted(by_season.keys(), reverse=True):
        stats = by_season[season]
        result.append(SeasonAveragesRow(
            season=season,
            games_played=len(stats),
            points=_avg(stats, "points"),
            rebounds=_avg(stats, "rebounds"),
            assists=_avg(stats, "assists"),
            passing_yards=_avg(stats, "passing_yards"),
            passing_completions=_avg(stats, "passing_completions"),
            passing_attempts=_avg(stats, "passing_attempts"),
            interceptions=_avg(stats, "interceptions"),
            rushing_yards=_avg(stats, "rushing_yards"),
            rushing_attempts=_avg(stats, "rushing_attempts"),
            receiving_yards=_avg(stats, "receiving_yards"),
            receptions=_avg(stats, "receptions"),
            targets=_avg(stats, "targets"),
            touchdowns=_avg(stats, "touchdowns"),
            sacks=_avg(stats, "sacks"),
            fumbles_lost=_avg(stats, "fumbles_lost"),
            usage_rate=_avg(stats, "usage_rate"),
        ))
    return result


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
                "passing_completions": stat.passing_completions,
                "passing_attempts": stat.passing_attempts,
                "interceptions": stat.interceptions,
                "rushing_yards": stat.rushing_yards,
                "rushing_attempts": stat.rushing_attempts,
                "receiving_yards": stat.receiving_yards,
                "receptions": stat.receptions,
                "targets": stat.targets,
                "touchdowns": stat.touchdowns,
                "sacks": stat.sacks,
                "fumbles_lost": stat.fumbles_lost,
                "usage_rate": stat.usage_rate,
            }.items()
            if value is not None
        }
        points.append(MetricSeriesPoint(game_id=game_id, game_date=game_date, metrics=metrics))
    return points
