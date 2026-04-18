from app.db.session import SessionLocal
from app.services.signal_generation_service import generate_signals


def main() -> int:
    with SessionLocal() as db:
        result = generate_signals(db)

    print(
        "Signal feature backfill complete: "
        f"signals_created={result.created_signals} "
        f"signals_updated={result.updated_signals} "
        f"rolling_metrics_created={result.created_rolling_metrics} "
        f"rolling_metrics_updated={result.updated_rolling_metrics}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
