from app.db.session import SessionLocal
from app.services.seed_service import seed_database


def main() -> int:
    with SessionLocal() as db:
        seed_database(db)

    print("Seeded Shyfty database.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
