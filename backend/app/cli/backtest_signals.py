import argparse
from pathlib import Path

from app.db.session import SessionLocal
from app.services.signal_backtest_service import run_signal_backtest, write_backtest_result


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay historical data and evaluate signal quality.")
    parser.add_argument(
        "--output",
        default="data/backtests/latest_signal_backtest.json",
        help="Output path for the JSON report.",
    )
    args = parser.parse_args()

    with SessionLocal() as db:
        result = run_signal_backtest(db)

    output_path = Path(args.output)
    write_backtest_result(result, output_path)
    print(
        "Backtest complete: "
        f"signals={result.summary['signal_count']} "
        f"precision_next_game={result.summary['precision_next_game']:.4f} "
        f"precision_next_3_games={result.summary['precision_next_3_games']:.4f} "
        f"output={output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
