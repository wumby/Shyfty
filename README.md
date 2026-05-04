# Shyfty

Shyfty is a signal-first sports product for NBA and NFL data. The product is no longer built around a fake seeded universe or deep archive browsing. The core loop is now: sync real provider data, generate signals, and show only the context needed to explain those signals.

## Direction

- No manual/demo seed step is required for app startup.
- The app can start against an empty database.
- Real data is pulled in through sync jobs and bootstrap ingestion.
- Current implementation supports real NBA sync and real NFL sync through ESPN public endpoints.
- No seeded/demo fallback should be used for either league.

## Architecture

- `backend/`
  FastAPI app, SQLAlchemy models, Alembic migrations, signal generation, and sync orchestration
- `scripts/`
  Thin operational wrappers for sync and inspection commands
- `web/`
  React + TypeScript + Vite client focused on the live signal workflow
- `ios/`
  SwiftUI client

## Backend Setup

1. `cd backend`
2. `python3 -m venv .venv`
3. `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `export DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/shyfty`
7. `alembic upgrade head`
8. `uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`

## Sync Workflow

From the repo root:

1. Bootstrap real NBA data into an empty or sparse database:
   `python scripts/run_sync.py --mode bootstrap --source nba --days-back 30 --max-games 50`
2. Bootstrap both real providers into an empty or sparse database:
   `python scripts/run_sync.py --mode bootstrap --source nba --source nfl --days-back 30 --max-games 50`
3. Run a smaller incremental refresh:
   `python scripts/run_sync.py --mode incremental --source nba --days-back 7 --max-games 50`
4. Run a smaller incremental refresh across all configured providers:
   `python scripts/run_sync.py --mode incremental`
5. Inspect ingest artifacts if needed:
   `python scripts/inspect_nba_ingest.py summary`

Schedule-first production sync (preferred):

1. Discover + hydrate in one pass for NBA:
   `python -m app.ingest.cli sync --league NBA`
2. Run all enabled leagues (production scheduler command):
   `python -m app.ingest.cli sync --all`
3. Backfill a range:
   `python -m app.ingest.cli sync --league NBA --from YYYY-MM-DD --to YYYY-MM-DD`
4. Force rehydrate a range:
   `python -m app.ingest.cli sync --league NBA --from YYYY-MM-DD --to YYYY-MM-DD --force`

Notes:

- Raw NBA payloads are stored under `data/raw/nba/`.
- NFL sync uses ESPN scoreboard + summary endpoints and falls back to the most recent completed weeks from the latest finished season during offseason.
- Sync runs are tracked in `ingest_runs`.
- Source checkpoints are tracked in `sync_checkpoints`.
- Games now retain `last_synced_at` and `signals_generated_at`.
- Default discovery window is yesterday/today/tomorrow (`SYNC_LOOKBACK_DAYS=1`, `SYNC_LOOKAHEAD_DAYS=1`).
- Final games can be rechecked for stat corrections within `STAT_CORRECTION_LOOKBACK_HOURS` (default `48`).
- Schedule-first sync is cheaper on provider API quotas because it hydrates only selected games instead of broad re-fetching.

## Reset Workflow

If an older local database still contains legacy seeded rows, especially fake NFL data:

- Remove only the legacy seeded NFL dataset:
  `python scripts/reset_data.py --mode legacy-seeded-nfl`
- Wipe all sports data and sync tracking while keeping user/auth tables:
  `python scripts/reset_data.py --mode sports-data`

## Web Setup

1. `cd web`
2. `npm install`
3. `npm run dev`

Optional combined startup:

- `bash scripts/reset-dev.sh`
- `DEV_SYNC_MAX_GAMES=25 bash scripts/reset-dev.sh`
- `BACKEND_HOST=127.0.0.1 DEV_FOREGROUND=1 BACKEND_RELOAD=0 OPEN_IOS_PROJECT=0 bash scripts/reset-dev.sh`

`scripts/reset-dev.sh` stops old backend/web/sync processes, applies migrations, starts a real NBA + NFL bootstrap sync, and starts the backend and web dev servers. It no longer seeds demo/sample rows. Use `DEV_SYNC_MAX_GAMES` to tune sync size, `BACKEND_HOST` to choose the bind host, and `DEV_FOREGROUND=1` when a caller needs the script to keep child processes attached.

## Product Scope

Kept:

- Signal feed
- Player and team pages that support the signal story
- Recent signal context and provenance
- Personalization (follows and feed preferences)

Deprioritized or being removed:

- Seed/demo workflows
- Fake NFL fallback data
- Deep basketball-reference-style history browsing
- Large game-log/archive surfaces that do not directly support signals

## Tests

- `bash scripts/test-backend.sh`
- `cd backend && PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$(pwd) .venv/bin/python -m unittest discover -s tests -p 'test_*.py'`

Unit tests may still use small deterministic fixtures, but the runtime app path no longer depends on seed scripts or demo data.

## Current Gaps

- Scheduler currently runs a simple once-daily sync model.
- ESPN endpoint stability/rate behavior can change over time because these are not a versioned paid feed.
- Additional source-specific checkpoints and incremental cursors can be layered onto the new sync tracking without redesigning the core flow.

## Production Deployment

Production deployment details are in [DEPLOYMENT.md](/Users/jackziegler/Projects/Shyfty/DEPLOYMENT.md:1), including:
- Railway backend + PostgreSQL setup
- static frontend deployment and `VITE_API_BASE_URL`
- CORS and cross-site cookie settings
- separate scheduled ingest job
- migration and rollback procedures
