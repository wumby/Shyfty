import argparse

from app.db.session import SessionLocal
from app.services.ingest_health_service import IngestHealthReport, inspect_ingest_health


def _fmt(value) -> str:
    return value.isoformat() if value is not None else "none"


def _print_report(report: IngestHealthReport) -> None:
    print(f"Ingest health: status={report.status}")
    print(
        "Freshness: "
        f"latest_final_game={_fmt(report.latest_final_game_date)} "
        f"latest_player_stats={_fmt(report.latest_player_stat_date)} "
        f"latest_team_stats={_fmt(report.latest_team_stat_date)} "
        f"latest_shyfts={_fmt(report.latest_shyft_date)}"
    )
    print(
        "Runs: "
        f"last_success={_fmt(report.last_successful_ingest_at)} "
        f"last_failed={_fmt(report.last_failed_ingest_at)}"
    )
    print(
        "Gaps: "
        f"final_missing_player_stats={report.final_games_missing_player_stats} "
        f"final_missing_team_stats={report.final_games_missing_team_stats} "
        f"non_final_player_stats={report.non_final_player_stats} "
        f"non_final_team_stats={report.non_final_team_stats} "
        f"non_final_shyfts={report.non_final_shyfts}"
    )
    print(
        "Rows: "
        f"games={report.games_count} player_stats={report.player_stats_count} "
        f"team_stats={report.team_stats_count} rolling_metrics={report.rolling_metrics_count} "
        f"shyfts={report.shyfts_count} raw_events={report.raw_events_count} "
        f"ingest_runs={report.ingest_runs_count}"
    )
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"- {warning}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect ingest freshness, final-game gaps, and DB row counts.")
    parser.add_argument("--final-game-lookback-days", type=int, default=14)
    parser.add_argument("--stale-after-days", type=int, default=2)
    args = parser.parse_args()

    with SessionLocal() as db:
        report = inspect_ingest_health(
            db,
            final_game_lookback_days=args.final_game_lookback_days,
            stale_after_days=args.stale_after_days,
        )

    _print_report(report)
    return 1 if report.status != "ok" else 0


if __name__ == "__main__":
    raise SystemExit(main())
