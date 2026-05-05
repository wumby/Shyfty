from app.db.session import SessionLocal
from app.services.shyft_generation_service import generate_shyfts


def main() -> int:
    with SessionLocal() as db:
        result = generate_shyfts(db)

    print(
        "Shyft feature backfill complete: "
        f"shyfts_created={result.created_shyfts} "
        f"shyfts_updated={result.updated_shyfts} "
        f"rolling_metrics_created={result.created_rolling_metrics} "
        f"rolling_metrics_updated={result.updated_rolling_metrics}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
