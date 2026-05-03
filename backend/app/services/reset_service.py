from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.comment_report import CommentReport
from app.models.game import Game
from app.models.ingest_run import IngestRun
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.raw_ingest_event import RawIngestEvent
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.signal_comment import SignalComment
from app.models.signal_reaction import SignalReaction
from app.models.sync_checkpoint import SyncCheckpoint
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.models.user_follow import UserFollow


@dataclass(frozen=True)
class ResetResult:
    mode: str
    leagues_deleted: int = 0
    teams_deleted: int = 0
    players_deleted: int = 0
    games_deleted: int = 0
    player_stats_deleted: int = 0
    team_stats_deleted: int = 0
    rolling_metrics_deleted: int = 0
    baseline_samples_deleted: int = 0
    signals_deleted: int = 0
    reactions_deleted: int = 0
    comments_deleted: int = 0
    reports_deleted: int = 0
    follows_deleted: int = 0
    raw_events_deleted: int = 0
    ingest_runs_deleted: int = 0
    sync_checkpoints_deleted: int = 0


def _count_scalar(db: Session, statement) -> int:
    return int(db.execute(statement).scalar_one())


def reset_legacy_seeded_nfl(db: Session, *, dry_run: bool = False) -> ResetResult:
    nfl_league_ids = select(League.id).where(League.name == "NFL")
    seeded_team_ids = select(Team.id).where(
        Team.league_id.in_(nfl_league_ids),
        Team.source_system.is_(None),
        Team.source_id.is_(None),
    )
    seeded_player_ids = select(Player.id).where(
        Player.league_id.in_(nfl_league_ids),
        Player.source_system.is_(None),
        Player.source_id.is_(None),
    )
    seeded_game_ids = select(Game.id).where(Game.league_id.in_(nfl_league_ids))
    seeded_signal_ids = select(Signal.id).where(Signal.league_id.in_(nfl_league_ids))
    seeded_comment_ids = select(SignalComment.id).where(SignalComment.signal_id.in_(seeded_signal_ids))
    seeded_rolling_metric_ids = select(RollingMetric.id).where(
        RollingMetric.player_id.in_(seeded_player_ids)
    )

    counts = {
        "leagues_deleted": _count_scalar(db, select(func.count()).select_from(League).where(League.id.in_(nfl_league_ids))),
        "teams_deleted": _count_scalar(db, select(func.count()).select_from(Team).where(Team.id.in_(seeded_team_ids))),
        "players_deleted": _count_scalar(db, select(func.count()).select_from(Player).where(Player.id.in_(seeded_player_ids))),
        "games_deleted": _count_scalar(db, select(func.count()).select_from(Game).where(Game.id.in_(seeded_game_ids))),
        "player_stats_deleted": _count_scalar(db, select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.player_id.in_(seeded_player_ids))),
        "team_stats_deleted": _count_scalar(db, select(func.count()).select_from(TeamGameStat).where(TeamGameStat.team_id.in_(seeded_team_ids))),
        "rolling_metrics_deleted": _count_scalar(db, select(func.count()).select_from(RollingMetric).where(RollingMetric.id.in_(seeded_rolling_metric_ids))),
        "baseline_samples_deleted": _count_scalar(db, select(func.count()).select_from(RollingMetricBaselineSample).where(RollingMetricBaselineSample.rolling_metric_id.in_(seeded_rolling_metric_ids))),
        "signals_deleted": _count_scalar(db, select(func.count()).select_from(Signal).where(Signal.id.in_(seeded_signal_ids))),
        "reactions_deleted": _count_scalar(db, select(func.count()).select_from(SignalReaction).where(SignalReaction.signal_id.in_(seeded_signal_ids))),
        "comments_deleted": _count_scalar(db, select(func.count()).select_from(SignalComment).where(SignalComment.id.in_(seeded_comment_ids))),
        "reports_deleted": _count_scalar(db, select(func.count()).select_from(CommentReport).where(CommentReport.comment_id.in_(seeded_comment_ids))),
        "follows_deleted": _count_scalar(
            db,
            select(func.count()).select_from(UserFollow).where(
                (UserFollow.entity_type == "player") & (UserFollow.entity_id.in_(seeded_player_ids))
                | (UserFollow.entity_type == "team") & (UserFollow.entity_id.in_(seeded_team_ids))
            ),
        ),
    }

    if not dry_run:
        db.execute(delete(CommentReport).where(CommentReport.comment_id.in_(seeded_comment_ids)))
        db.execute(delete(SignalReaction).where(SignalReaction.signal_id.in_(seeded_signal_ids)))
        db.execute(
            delete(UserFollow).where(
                ((UserFollow.entity_type == "player") & (UserFollow.entity_id.in_(seeded_player_ids)))
                | ((UserFollow.entity_type == "team") & (UserFollow.entity_id.in_(seeded_team_ids)))
            )
        )
        db.execute(delete(SignalComment).where(SignalComment.id.in_(seeded_comment_ids)))
        db.execute(delete(Signal).where(Signal.id.in_(seeded_signal_ids)))
        db.execute(delete(RollingMetricBaselineSample).where(RollingMetricBaselineSample.rolling_metric_id.in_(seeded_rolling_metric_ids)))
        db.execute(delete(RollingMetric).where(RollingMetric.id.in_(seeded_rolling_metric_ids)))
        db.execute(delete(PlayerGameStat).where(PlayerGameStat.player_id.in_(seeded_player_ids)))
        db.execute(delete(TeamGameStat).where(TeamGameStat.team_id.in_(seeded_team_ids)))
        db.execute(delete(Game).where(Game.id.in_(seeded_game_ids)))
        db.execute(delete(Player).where(Player.id.in_(seeded_player_ids)))
        db.execute(delete(Team).where(Team.id.in_(seeded_team_ids)))
        db.execute(delete(League).where(League.id.in_(nfl_league_ids)))
        db.commit()

    return ResetResult(mode="legacy-seeded-nfl", **counts)


def reset_sports_data(db: Session, *, dry_run: bool = False) -> ResetResult:
    league_ids = select(League.id)
    team_ids = select(Team.id)
    player_ids = select(Player.id)
    game_ids = select(Game.id)
    signal_ids = select(Signal.id)
    comment_ids = select(SignalComment.id)
    rolling_metric_ids = select(RollingMetric.id)

    counts = {
        "leagues_deleted": _count_scalar(db, select(func.count()).select_from(League)),
        "teams_deleted": _count_scalar(db, select(func.count()).select_from(Team)),
        "players_deleted": _count_scalar(db, select(func.count()).select_from(Player)),
        "games_deleted": _count_scalar(db, select(func.count()).select_from(Game)),
        "player_stats_deleted": _count_scalar(db, select(func.count()).select_from(PlayerGameStat)),
        "team_stats_deleted": _count_scalar(db, select(func.count()).select_from(TeamGameStat)),
        "rolling_metrics_deleted": _count_scalar(db, select(func.count()).select_from(RollingMetric)),
        "baseline_samples_deleted": _count_scalar(db, select(func.count()).select_from(RollingMetricBaselineSample)),
        "signals_deleted": _count_scalar(db, select(func.count()).select_from(Signal)),
        "reactions_deleted": _count_scalar(db, select(func.count()).select_from(SignalReaction)),
        "comments_deleted": _count_scalar(db, select(func.count()).select_from(SignalComment)),
        "reports_deleted": _count_scalar(db, select(func.count()).select_from(CommentReport)),
        "follows_deleted": _count_scalar(
            db,
            select(func.count()).select_from(UserFollow).where(
                ((UserFollow.entity_type == "player") & (UserFollow.entity_id.in_(player_ids)))
                | ((UserFollow.entity_type == "team") & (UserFollow.entity_id.in_(team_ids)))
            ),
        ),
        "raw_events_deleted": _count_scalar(db, select(func.count()).select_from(RawIngestEvent)),
        "ingest_runs_deleted": _count_scalar(db, select(func.count()).select_from(IngestRun)),
        "sync_checkpoints_deleted": _count_scalar(db, select(func.count()).select_from(SyncCheckpoint)),
    }

    if not dry_run:
        db.execute(delete(CommentReport).where(CommentReport.comment_id.in_(comment_ids)))
        db.execute(delete(SignalReaction).where(SignalReaction.signal_id.in_(signal_ids)))
        db.execute(
            delete(UserFollow).where(
                ((UserFollow.entity_type == "player") & (UserFollow.entity_id.in_(player_ids)))
                | ((UserFollow.entity_type == "team") & (UserFollow.entity_id.in_(team_ids)))
            )
        )
        db.execute(delete(SignalComment))
        db.execute(delete(Signal))
        db.execute(delete(RollingMetricBaselineSample).where(RollingMetricBaselineSample.rolling_metric_id.in_(rolling_metric_ids)))
        db.execute(delete(RollingMetric))
        db.execute(delete(PlayerGameStat))
        db.execute(delete(TeamGameStat))
        db.execute(delete(Game))
        db.execute(delete(Player))
        db.execute(delete(Team))
        db.execute(delete(League))
        db.execute(delete(RawIngestEvent))
        db.execute(delete(IngestRun))
        db.execute(delete(SyncCheckpoint))
        db.commit()

    return ResetResult(mode="sports-data", **counts)
