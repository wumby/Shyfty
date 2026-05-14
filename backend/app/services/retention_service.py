from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.models.comment_report import CommentReport
from app.models.game import Game
from app.models.ingest_run import IngestRun
from app.models.player_game_stat import PlayerGameStat
from app.models.raw_ingest_event import RawIngestEvent
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.shyft import Shyft
from app.models.shyft_comment import ShyftComment
from app.models.shyft_reaction import ShyftReactionRecord
from app.models.team_game_stat import TeamGameStat


NON_FINAL_GENERATED_STATUSES = ("live", "scheduled")


@dataclass(frozen=True)
class RetentionResult:
    dry_run: bool
    sports_cutoff: date
    raw_ingest_cutoff: datetime
    ingest_run_cutoff: datetime
    games_deleted: int = 0
    player_stats_deleted: int = 0
    team_stats_deleted: int = 0
    rolling_metrics_deleted: int = 0
    baseline_samples_deleted: int = 0
    shyfts_deleted: int = 0
    reactions_deleted: int = 0
    comments_deleted: int = 0
    reports_deleted: int = 0
    raw_events_deleted: int = 0
    ingest_runs_deleted: int = 0

    @property
    def total_deleted(self) -> int:
        return (
            self.games_deleted
            + self.player_stats_deleted
            + self.team_stats_deleted
            + self.rolling_metrics_deleted
            + self.baseline_samples_deleted
            + self.shyfts_deleted
            + self.reactions_deleted
            + self.comments_deleted
            + self.reports_deleted
            + self.raw_events_deleted
            + self.ingest_runs_deleted
    )


@dataclass(frozen=True)
class NonFinalGeneratedCleanupResult:
    dry_run: bool
    statuses: tuple[str, ...]
    player_stats_deleted: int = 0
    team_stats_deleted: int = 0
    rolling_metrics_deleted: int = 0
    baseline_samples_deleted: int = 0
    shyfts_deleted: int = 0
    reactions_deleted: int = 0
    comments_deleted: int = 0
    reports_deleted: int = 0
    games_touched: int = 0

    @property
    def total_deleted(self) -> int:
        return (
            self.player_stats_deleted
            + self.team_stats_deleted
            + self.rolling_metrics_deleted
            + self.baseline_samples_deleted
            + self.shyfts_deleted
            + self.reactions_deleted
            + self.comments_deleted
            + self.reports_deleted
        )


def _count_scalar(db: Session, statement) -> int:
    return int(db.execute(statement).scalar_one())


def _execute_delete(db: Session, statement) -> None:
    db.execute(statement.execution_options(synchronize_session=False))


def prune_retained_data(
    db: Session,
    *,
    sports_days: int,
    raw_ingest_days: int,
    ingest_run_days: int,
    dry_run: bool = False,
    now: datetime | None = None,
) -> RetentionResult:
    """Prune bounded operational data while keeping durable dimensions and users.

    Sports facts are pruned by game date. Leagues, teams, players, users, follows,
    preferences, sessions, and sync checkpoints are intentionally retained.
    """
    if sports_days < 1:
        raise ValueError("sports_days must be at least 1")
    if raw_ingest_days < 1:
        raise ValueError("raw_ingest_days must be at least 1")
    if ingest_run_days < 1:
        raise ValueError("ingest_run_days must be at least 1")

    now_dt = now or datetime.utcnow()
    sports_cutoff = now_dt.date() - timedelta(days=sports_days)
    raw_ingest_cutoff = now_dt - timedelta(days=raw_ingest_days)
    ingest_run_cutoff = now_dt - timedelta(days=ingest_run_days)

    old_game_ids = select(Game.id).where(Game.game_date < sports_cutoff)
    old_shyft_ids = select(Shyft.id).where(Shyft.game_id.in_(old_game_ids))
    old_comment_ids = select(ShyftComment.id).where(ShyftComment.shyft_id.in_(old_shyft_ids))
    old_player_stat_ids = select(PlayerGameStat.id).where(PlayerGameStat.game_id.in_(old_game_ids))
    old_rolling_metric_ids = select(RollingMetric.id).where(RollingMetric.game_id.in_(old_game_ids))

    counts = {
        "games_deleted": _count_scalar(db, select(func.count()).select_from(Game).where(Game.id.in_(old_game_ids))),
        "player_stats_deleted": _count_scalar(
            db, select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.id.in_(old_player_stat_ids))
        ),
        "team_stats_deleted": _count_scalar(
            db, select(func.count()).select_from(TeamGameStat).where(TeamGameStat.game_id.in_(old_game_ids))
        ),
        "rolling_metrics_deleted": _count_scalar(
            db, select(func.count()).select_from(RollingMetric).where(RollingMetric.id.in_(old_rolling_metric_ids))
        ),
        "baseline_samples_deleted": _count_scalar(
            db,
            select(func.count())
            .select_from(RollingMetricBaselineSample)
            .where(
                or_(
                    RollingMetricBaselineSample.rolling_metric_id.in_(old_rolling_metric_ids),
                    RollingMetricBaselineSample.player_game_stat_id.in_(old_player_stat_ids),
                )
            ),
        ),
        "shyfts_deleted": _count_scalar(db, select(func.count()).select_from(Shyft).where(Shyft.id.in_(old_shyft_ids))),
        "reactions_deleted": _count_scalar(
            db, select(func.count()).select_from(ShyftReactionRecord).where(ShyftReactionRecord.shyft_id.in_(old_shyft_ids))
        ),
        "comments_deleted": _count_scalar(
            db, select(func.count()).select_from(ShyftComment).where(ShyftComment.id.in_(old_comment_ids))
        ),
        "reports_deleted": _count_scalar(
            db, select(func.count()).select_from(CommentReport).where(CommentReport.comment_id.in_(old_comment_ids))
        ),
        "raw_events_deleted": _count_scalar(
            db, select(func.count()).select_from(RawIngestEvent).where(RawIngestEvent.ingested_at < raw_ingest_cutoff)
        ),
        "ingest_runs_deleted": _count_scalar(
            db, select(func.count()).select_from(IngestRun).where(IngestRun.started_at < ingest_run_cutoff)
        ),
    }

    if not dry_run:
        _execute_delete(db, delete(CommentReport).where(CommentReport.comment_id.in_(old_comment_ids)))
        _execute_delete(db, delete(ShyftReactionRecord).where(ShyftReactionRecord.shyft_id.in_(old_shyft_ids)))
        _execute_delete(db, delete(ShyftComment).where(ShyftComment.id.in_(old_comment_ids)))
        _execute_delete(db, delete(Shyft).where(Shyft.id.in_(old_shyft_ids)))
        _execute_delete(
            db,
            delete(RollingMetricBaselineSample).where(
                or_(
                    RollingMetricBaselineSample.rolling_metric_id.in_(old_rolling_metric_ids),
                    RollingMetricBaselineSample.player_game_stat_id.in_(old_player_stat_ids),
                )
            ),
        )
        _execute_delete(db, delete(RollingMetric).where(RollingMetric.id.in_(old_rolling_metric_ids)))
        _execute_delete(db, delete(PlayerGameStat).where(PlayerGameStat.id.in_(old_player_stat_ids)))
        _execute_delete(db, delete(TeamGameStat).where(TeamGameStat.game_id.in_(old_game_ids)))
        _execute_delete(db, delete(Game).where(Game.id.in_(old_game_ids)))
        _execute_delete(db, delete(RawIngestEvent).where(RawIngestEvent.ingested_at < raw_ingest_cutoff))
        _execute_delete(db, delete(IngestRun).where(IngestRun.started_at < ingest_run_cutoff))
        db.commit()

    return RetentionResult(
        dry_run=dry_run,
        sports_cutoff=sports_cutoff,
        raw_ingest_cutoff=raw_ingest_cutoff,
        ingest_run_cutoff=ingest_run_cutoff,
        **counts,
    )


def cleanup_non_final_generated_data(
    db: Session,
    *,
    statuses: tuple[str, ...] = NON_FINAL_GENERATED_STATUSES,
    dry_run: bool = False,
) -> NonFinalGeneratedCleanupResult:
    """Remove generated artifacts for known non-final games while keeping game rows.

    This intentionally defaults to explicit live/scheduled statuses only. It does
    not treat "unknown" as non-final because older completed provider rows may use
    that status.
    """
    normalized_statuses = tuple(status.strip().lower() for status in statuses if status.strip())
    if not normalized_statuses:
        raise ValueError("At least one status is required")
    if "unknown" in normalized_statuses:
        raise ValueError("Refusing to cleanup status='unknown'; it may contain completed historical games")
    if "final" in normalized_statuses:
        raise ValueError("Refusing to cleanup status='final'")

    target_game_ids = select(Game.id).where(func.lower(Game.status).in_(normalized_statuses))
    target_shyft_ids = select(Shyft.id).where(Shyft.game_id.in_(target_game_ids))
    target_comment_ids = select(ShyftComment.id).where(ShyftComment.shyft_id.in_(target_shyft_ids))
    target_player_stat_ids = select(PlayerGameStat.id).where(PlayerGameStat.game_id.in_(target_game_ids))
    target_rolling_metric_ids = select(RollingMetric.id).where(RollingMetric.game_id.in_(target_game_ids))

    counts = {
        "games_touched": _count_scalar(db, select(func.count()).select_from(Game).where(Game.id.in_(target_game_ids))),
        "player_stats_deleted": _count_scalar(
            db, select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.id.in_(target_player_stat_ids))
        ),
        "team_stats_deleted": _count_scalar(
            db, select(func.count()).select_from(TeamGameStat).where(TeamGameStat.game_id.in_(target_game_ids))
        ),
        "rolling_metrics_deleted": _count_scalar(
            db, select(func.count()).select_from(RollingMetric).where(RollingMetric.id.in_(target_rolling_metric_ids))
        ),
        "baseline_samples_deleted": _count_scalar(
            db,
            select(func.count())
            .select_from(RollingMetricBaselineSample)
            .where(
                or_(
                    RollingMetricBaselineSample.rolling_metric_id.in_(target_rolling_metric_ids),
                    RollingMetricBaselineSample.player_game_stat_id.in_(target_player_stat_ids),
                )
            ),
        ),
        "shyfts_deleted": _count_scalar(db, select(func.count()).select_from(Shyft).where(Shyft.id.in_(target_shyft_ids))),
        "reactions_deleted": _count_scalar(
            db, select(func.count()).select_from(ShyftReactionRecord).where(ShyftReactionRecord.shyft_id.in_(target_shyft_ids))
        ),
        "comments_deleted": _count_scalar(
            db, select(func.count()).select_from(ShyftComment).where(ShyftComment.id.in_(target_comment_ids))
        ),
        "reports_deleted": _count_scalar(
            db, select(func.count()).select_from(CommentReport).where(CommentReport.comment_id.in_(target_comment_ids))
        ),
    }

    if not dry_run:
        _execute_delete(db, delete(CommentReport).where(CommentReport.comment_id.in_(target_comment_ids)))
        _execute_delete(db, delete(ShyftReactionRecord).where(ShyftReactionRecord.shyft_id.in_(target_shyft_ids)))
        _execute_delete(db, delete(ShyftComment).where(ShyftComment.id.in_(target_comment_ids)))
        _execute_delete(db, delete(Shyft).where(Shyft.id.in_(target_shyft_ids)))
        _execute_delete(
            db,
            delete(RollingMetricBaselineSample).where(
                or_(
                    RollingMetricBaselineSample.rolling_metric_id.in_(target_rolling_metric_ids),
                    RollingMetricBaselineSample.player_game_stat_id.in_(target_player_stat_ids),
                )
            ),
        )
        _execute_delete(db, delete(RollingMetric).where(RollingMetric.id.in_(target_rolling_metric_ids)))
        _execute_delete(db, delete(PlayerGameStat).where(PlayerGameStat.id.in_(target_player_stat_ids)))
        _execute_delete(db, delete(TeamGameStat).where(TeamGameStat.game_id.in_(target_game_ids)))
        db.commit()

    return NonFinalGeneratedCleanupResult(
        dry_run=dry_run,
        statuses=normalized_statuses,
        **counts,
    )
