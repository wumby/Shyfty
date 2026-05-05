from app.db.session import SessionLocal
from app.services.shyft_generation_service import ShyftGenerationError, generate_shyfts


def main() -> int:
    with SessionLocal() as db:
        try:
            result = generate_shyfts(db)
        except ShyftGenerationError as exc:
            print(str(exc))
            print(f"Partial result before rollback: {exc.partial_result}")
            return 1

    print(
        "Generated shyfts: "
        f"created={result.created_shyfts}, "
        f"updated={result.updated_shyfts}, "
        f"deleted={result.deleted_shyfts}, "
        f"rolling_created={result.created_rolling_metrics}, "
        f"rolling_updated={result.updated_rolling_metrics}, "
        f"rolling_deleted={result.deleted_rolling_metrics}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
