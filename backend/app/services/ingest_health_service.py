from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.ingest_run import IngestRun
from app.models.player_game_stat import PlayerGameStat
from app.models.raw_ingest_event import RawIngestEvent
from app.models.rolling_metric import RollingMetric
from app.models.shyft import Shyft
from app.models.team_game_stat import TeamGameStat

NON_FINAL_PUBLISH_STATUSES = ("live", "scheduled")


@dataclass(frozen=True)
class IngestHealthReport:
    status: str
    warnings: list[str] = field(default_factory=list)
    latest_final_game_date: Optional[date] = None
    latest_player_stat_date: Optional[date] = None
    latest_team_stat_date: Optional[date] = None
    latest_shyft_date: Optional[date] = None
    last_successful_ingest_at: Optional[datetime] = None
    last_failed_ingest_at: Optional[datetime] = None
    final_games_missing_player_stats: int = 0
    final_games_missing_team_stats: int = 0
    non_final_player_stats: int = 0
    non_final_team_stats: int = 0
    non_final_shyfts: int = 0
    games_count: int = 0
    player_stats_count: int = 0
    team_stats_count: int = 0
    rolling_metrics_count: int = 0
    shyfts_count: int = 0
    raw_events_count: int = 0
    ingest_runs_count: int = 0


def _scalar(db: Session, statement):
    return db.execute(statement).scalar_one()


def _count(db: Session, statement) -> int:
    return int(_scalar(db, statement))


def inspect_ingest_health(
    db: Session,
    *,
    final_game_lookback_days: int = 14,
    stale_after_days: int = 2,
    now: Optional[datetime] = None,
) -> IngestHealthReport:
    if final_game_lookback_days < 1:
        raise ValueError("final_game_lookback_days must be at least 1")
    if stale_after_days < 1:
        raise ValueError("stale_after_days must be at least 1")

    now_dt = now or datetime.utcnow()
    final_cutoff = now_dt.date() - timedelta(days=final_game_lookback_days)
    stale_cutoff = now_dt.date() - timedelta(days=stale_after_days)

    latest_final_game_date = _scalar(
        db,
        select(func.max(Game.game_date)).where(func.lower(Game.status) == "final"),
    )
    latest_player_stat_date = _scalar(
        db,
        select(func.max(Game.game_date)).join(PlayerGameStat, PlayerGameStat.game_id == Game.id),
    )
    latest_team_stat_date = _scalar(
        db,
        select(func.max(Game.game_date)).join(TeamGameStat, TeamGameStat.game_id == Game.id),
    )
    latest_shyft_date = _scalar(
        db,
        select(func.max(Game.game_date)).join(Shyft, Shyft.game_id == Game.id),
    )
    last_successful_ingest_at = _scalar(
        db,
        select(func.max(IngestRun.finished_at)).where(IngestRun.status == "success"),
    )
    last_failed_ingest_at = _scalar(
        db,
        select(func.max(IngestRun.finished_at)).where(IngestRun.status == "failed"),
    )

    final_recent_game_ids = select(Game.id).where(
        func.lower(Game.status) == "final",
        Game.game_date >= final_cutoff,
    )
    non_final_game_ids = select(Game.id).where(func.lower(Game.status).in_(NON_FINAL_PUBLISH_STATUSES))

    final_games_missing_player_stats = _count(
        db,
        select(func.count()).select_from(Game).where(
            Game.id.in_(final_recent_game_ids),
            ~Game.id.in_(select(PlayerGameStat.game_id)),
        ),
    )
    final_games_missing_team_stats = _count(
        db,
        select(func.count()).select_from(Game).where(
            Game.id.in_(final_recent_game_ids),
            ~Game.id.in_(select(TeamGameStat.game_id)),
        ),
    )
    non_final_player_stats = _count(
        db,
        select(func.count()).select_from(PlayerGameStat).where(PlayerGameStat.game_id.in_(non_final_game_ids)),
    )
    non_final_team_stats = _count(
        db,
        select(func.count()).select_from(TeamGameStat).where(TeamGameStat.game_id.in_(non_final_game_ids)),
    )
    non_final_shyfts = _count(
        db,
        select(func.count()).select_from(Shyft).where(Shyft.game_id.in_(non_final_game_ids)),
    )

    warnings: list[str] = []
    if latest_final_game_date and latest_player_stat_date and latest_player_stat_date < latest_final_game_date:
        warnings.append("latest player stats are behind the latest final game")
    if latest_player_stat_date and latest_shyft_date and latest_shyft_date < latest_player_stat_date:
        warnings.append("latest shyfts are behind latest player stats")
    if latest_shyft_date is None:
        warnings.append("no shyfts have been generated")
    elif latest_shyft_date < stale_cutoff:
        warnings.append(f"latest shyft date is older than {stale_after_days} days")
    if final_games_missing_player_stats:
        warnings.append(f"{final_games_missing_player_stats} recent final games are missing player stats")
    if final_games_missing_team_stats:
        warnings.append(f"{final_games_missing_team_stats} recent final games are missing team stats")
    if non_final_player_stats or non_final_team_stats or non_final_shyfts:
        warnings.append("live/scheduled games have generated stats or shyfts")

    return IngestHealthReport(
        status="warning" if warnings else "ok",
        warnings=warnings,
        latest_final_game_date=latest_final_game_date,
        latest_player_stat_date=latest_player_stat_date,
        latest_team_stat_date=latest_team_stat_date,
        latest_shyft_date=latest_shyft_date,
        last_successful_ingest_at=last_successful_ingest_at,
        last_failed_ingest_at=last_failed_ingest_at,
        final_games_missing_player_stats=final_games_missing_player_stats,
        final_games_missing_team_stats=final_games_missing_team_stats,
        non_final_player_stats=non_final_player_stats,
        non_final_team_stats=non_final_team_stats,
        non_final_shyfts=non_final_shyfts,
        games_count=_count(db, select(func.count()).select_from(Game)),
        player_stats_count=_count(db, select(func.count()).select_from(PlayerGameStat)),
        team_stats_count=_count(db, select(func.count()).select_from(TeamGameStat)),
        rolling_metrics_count=_count(db, select(func.count()).select_from(RollingMetric)),
        shyfts_count=_count(db, select(func.count()).select_from(Shyft)),
        raw_events_count=_count(db, select(func.count()).select_from(RawIngestEvent)),
        ingest_runs_count=_count(db, select(func.count()).select_from(IngestRun)),
    )
