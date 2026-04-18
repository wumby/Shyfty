from app.db.session import SessionLocal
from app.services.signal_generation_service import SignalGenerationError, generate_signals


def main() -> int:
    with SessionLocal() as db:
        try:
            result = generate_signals(db)
        except SignalGenerationError as exc:
            print(str(exc))
            print(f"Partial result before rollback: {exc.partial_result}")
            return 1

    print(
        "Generated signals: "
        f"created={result.created_signals}, "
        f"updated={result.updated_signals}, "
        f"deleted={result.deleted_signals}, "
        f"rolling_created={result.created_rolling_metrics}, "
        f"rolling_updated={result.updated_rolling_metrics}, "
        f"rolling_deleted={result.deleted_rolling_metrics}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
