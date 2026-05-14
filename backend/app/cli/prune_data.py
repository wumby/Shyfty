import argparse

from app.core.config import settings
from app.db.session import SessionLocal
from app.services.retention_service import (
    NonFinalGeneratedCleanupResult,
    RetentionResult,
    cleanup_non_final_generated_data,
    prune_retained_data,
)


def _print_result(result: RetentionResult) -> None:
    label = "Dry run" if result.dry_run else "Prune complete"
    print(
        f"{label}: sports_before={result.sports_cutoff.isoformat()} "
        f"raw_ingest_before={result.raw_ingest_cutoff.isoformat()} "
        f"ingest_runs_before={result.ingest_run_cutoff.isoformat()} "
        f"total={result.total_deleted} games={result.games_deleted} "
        f"player_stats={result.player_stats_deleted} team_stats={result.team_stats_deleted} "
        f"rolling_metrics={result.rolling_metrics_deleted} baseline_samples={result.baseline_samples_deleted} "
        f"shyfts={result.shyfts_deleted} comments={result.comments_deleted} reactions={result.reactions_deleted} "
        f"reports={result.reports_deleted} raw_events={result.raw_events_deleted} ingest_runs={result.ingest_runs_deleted}"
    )


def _print_non_final_result(result: NonFinalGeneratedCleanupResult) -> None:
    label = "Non-final dry run" if result.dry_run else "Non-final cleanup complete"
    print(
        f"{label}: statuses={','.join(result.statuses)} games_touched={result.games_touched} "
        f"total={result.total_deleted} player_stats={result.player_stats_deleted} "
        f"team_stats={result.team_stats_deleted} rolling_metrics={result.rolling_metrics_deleted} "
        f"baseline_samples={result.baseline_samples_deleted} shyfts={result.shyfts_deleted} "
        f"comments={result.comments_deleted} reactions={result.reactions_deleted} reports={result.reports_deleted}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prune old Shyfty operational data using configured retention windows.")
    parser.add_argument("--sports-days", type=int, default=settings.retention_sports_days)
    parser.add_argument("--raw-ingest-days", type=int, default=settings.retention_raw_ingest_days)
    parser.add_argument("--ingest-run-days", type=int, default=settings.retention_ingest_run_days)
    parser.add_argument("--dry-run", action="store_true", help="Report what would be deleted without modifying the database.")
    parser.add_argument(
        "--cleanup-non-final",
        action="store_true",
        help="Also remove generated stats/shyfts for explicitly live/scheduled games, keeping game rows.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        if args.cleanup_non_final:
            non_final_result = cleanup_non_final_generated_data(db, dry_run=args.dry_run)
            _print_non_final_result(non_final_result)

        result = prune_retained_data(
            db,
            sports_days=args.sports_days,
            raw_ingest_days=args.raw_ingest_days,
            ingest_run_days=args.ingest_run_days,
            dry_run=args.dry_run,
        )

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
