# Shyfty

Shyfty is a sports signal engine for NBA and NFL player volatility. The product surfaces spikes, drops, shifts, consistency, and outlier events as a real-time feed rather than a traditional stats dashboard.

## Architecture

Text diagram:

- `backend/`
  FastAPI app with SQLAlchemy models, Alembic-managed schema, domain logic, REST endpoints, and Postgres persistence
- `scripts/`
  Thin operational entrypoints for seeding and signal generation
- `web/`
  React + TypeScript + Vite client using Zustand, React Router, Tailwind, and Recharts
- `ios/`
  SwiftUI client using URLSession, NavigationStack, and Swift Charts
- `infra/`
  Docker Compose for Postgres and the backend API

## Folder Structure

```text
Shyfty/
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── models/
│   │   ├── schemas/
│   │   └── services/
│   ├── Dockerfile
│   └── requirements.txt
├── infra/
│   └── docker-compose.yml
├── ios/
│   └── Shyfty/
│       ├── Shyfty/
│       └── Shyfty.xcodeproj/
├── scripts/
│   ├── run_signal_engine.py
│   └── seed_db.py
└── web/
    ├── src/
    │   ├── components/
    │   ├── pages/
    │   ├── services/
    │   ├── store/
    │   └── types/
    └── package.json
```

## Backend Setup

### Option 1: Docker

1. `cd infra`
2. `docker compose up --build -d`

Then seed and generate signals from the repo root:

1. `cd backend`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/shyfty`
6. `alembic upgrade head`
7. `python ../scripts/seed_db.py`
8. `python ../scripts/run_signal_engine.py`

### Option 2: Local backend only

1. Start Postgres locally
2. `cd backend`
3. `python3 -m venv .venv`
4. `source .venv/bin/activate`
5. `pip install -r requirements.txt`
6. `export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/shyfty`
7. `alembic upgrade head`
8. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`

## NBA Ingestion Workflow

The preferred local validation path is now NBA-only raw ingestion instead of the hand-seeded demo dataset.

Commands from the repo root:

1. Fetch recent NBA raw payloads
   `python scripts/fetch_nba_data.py --season 2024-25 --days-back 21 --max-games 20`
2. Normalize the latest raw snapshot into canonical tables
   `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/load_nba_data.py`
3. Generate signals from the normalized data
   `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/run_signal_engine.py`

Inspection helpers:

- `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/inspect_nba_ingest.py summary`
- `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/inspect_nba_ingest.py games --limit 10`
- `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/inspect_nba_ingest.py players --limit 20`
- `DATABASE_URL=sqlite:////Users/jackziegler/Projects/Shyfty/shyfty.db python scripts/inspect_signals.py signal <signal_id>`

Raw payloads are stored under `data/raw/nba/` and the latest fetched snapshot path is recorded in `data/raw/nba/LATEST`.
Normalized `player_game_stats` rows now retain source IDs and raw snapshot file references so signal traces can be followed from the product layer back to canonical rows and local raw payload files.

## Web Setup

1. `cd web`
2. `npm install`
3. `npm run dev`

Optional:

- `VITE_API_BASE_URL=http://127.0.0.1:8001/api npm run dev`
- `scripts/start-dev.sh` now supports integrated seeding through env vars:
- `SHYFTY_DEV_SEED_MODE=auto|real|demo|skip` where `auto` seeds real NBA data only when `player_game_stats` is empty
- `SHYFTY_DEV_SEED_SEASON=2024-25 SHYFTY_DEV_SEED_DAYS_BACK=21 SHYFTY_DEV_SEED_MAX_GAMES=20 bash scripts/start-dev.sh`
- `SHYFTY_DEV_SEED_INCLUDE_NFL=0 bash scripts/start-dev.sh`
- `scripts/stop-dev.sh` now also clears the transient `.run/seed.log`

## iOS Setup

1. Open [ios/Shyfty/Shyfty.xcodeproj](/Users/jackziegler/Projects/Shyfty/ios/Shyfty/Shyfty.xcodeproj)
2. Start the backend with `uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`
3. Run the `Shyfty` scheme in Xcode

Debug base URL behavior:

- iOS Simulator always uses `http://127.0.0.1:8001/api`
- Physical iPhone Debug builds use `http://192.168.0.28:8001/api`
- The physical-device Debug URL is supplied by the `SHYFTY_API_BASE_URL` build setting and injected into `ShyftyAPIBaseURL` in `Info-Debug.plist`

Notes:

- Your Mac and iPhone must be on the same local network for physical-device testing
- If your Mac’s LAN IP changes, update `SHYFTY_API_BASE_URL` in the Xcode project Debug build settings
- Debug builds include ATS exceptions for local HTTP access to `127.0.0.1` and `192.168.0.28`

## Seeding and Signal Generation

- Run migrations first: `cd backend && alembic upgrade head`
- `python scripts/seed_db.py`
- `python scripts/run_signal_engine.py`

`scripts/seed_db.py` and `scripts/run_signal_engine.py` are thin entrypoints over backend CLI modules.
Generation logic lives in `backend/app/domain/signals.py` and `backend/app/services/signal_generation_service.py`.

`python scripts/seed_db.py` now fetches and loads real NBA data by default, then adds the demo NFL fixture set. Useful flags:

- `python scripts/seed_db.py --generate-signals`
- `python scripts/seed_db.py --season 2024-25 --days-back 21 --max-games 20`
- `python scripts/seed_db.py --skip-nfl-demo`
- `python scripts/seed_db.py --demo-only`

The demo-only fallback dataset includes:

- NBA: Luka Doncic, Nikola Jokic, Stephen Curry
- NFL: Patrick Mahomes, Josh Allen, Justin Jefferson

The signal engine computes rolling averages, rolling standard deviation, z-scores, and writes signal records using these rules:

- `SPIKE`: `z >= 1.5`
- `DROP`: `z <= -1.5`
- `OUTLIER`: `|z| >= 2.5`
- `SHIFT`: usage-rate z-score magnitude `>= 1.0`
- `CONSISTENCY`: low recent variance

The generator now backfills all eligible historical game contexts, not just the latest one, and reruns update existing contexts instead of recreating duplicate rows.

## Tests

- `cd backend && .venv/bin/python -m unittest discover -s tests -q`

## API Overview

- `GET /api/health`
- `GET /api/signals`
- `GET /api/players`
- `GET /api/players/{id}`
- `GET /api/players/{id}/signals`
- `GET /api/players/{id}/metrics`
- `GET /api/teams`

## Real vs Mocked

Real:

- Postgres-backed schema
- Alembic-managed schema lifecycle
- Seeded player, team, game, stat, rolling metric, and signal records
- Signal generation service writing idempotent historical rolling metric and signal records
- Web and iOS clients fetching live API data

Mocked or simplified:

- NBA ingestion now loads recent raw payloads from `stats.nba.com` into canonical tables, but NFL remains seeded/demo-only
- No auth, favorites persistence, or push notifications
- No scheduler or background worker yet; ingestion is manual CLI-driven

## Next Steps To Productionize

1. Replace static seed inputs with sportsbook or official league data ingestion.
2. Add background jobs for scheduled recomputation and cache invalidation.
3. Add auth, saved filters, favorites persistence, and alert delivery.
4. Harden migrations, tests, observability, and deploy environments.

## Migration Notes

- The API no longer auto-creates tables on startup. Run `alembic upgrade head` before seeding or starting the backend against a fresh database.
- `0002_signal_generation_context` adds `game_id` to `signals` and `rolling_metrics`.
- Existing environments with data should apply Alembic before running the refactored signal engine so existing rows are backfilled with the latest known game context.
