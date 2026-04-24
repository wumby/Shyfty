# Shyfty

Shyfty is a signal-first sports product for NBA and NFL data. The product is no longer built around a fake seeded universe or deep archive browsing. The core loop is now: sync real provider data, generate signals, and show only the context needed to explain those signals.

## Direction

- No manual/demo seed step is required for app startup.
- The app can start against an empty database.
- Real data is pulled in through sync jobs and bootstrap ingestion.
- Current implementation supports real NBA sync and real NFL sync through SportsDataIO.
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
6. `export SPORTSDATAIO_NFL_API_KEY=your_real_key`
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

Notes:

- Raw NBA payloads are stored under `data/raw/nba/`.
- NFL sync uses SportsDataIO's weekly final box score feeds and falls back to the most recent completed weeks from the latest finished season during offseason.
- SportsDataIO's own documentation says the free trial uses scrambled data. For real NFL data, use a production or replay key only.
- Sync runs are tracked in `ingest_runs`.
- Source checkpoints are tracked in `sync_checkpoints`.
- Games now retain `last_synced_at` and `signals_generated_at`.

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

- `bash scripts/start-dev.sh`
- `SHYFTY_DEV_BOOTSTRAP_ON_START=1 bash scripts/start-dev.sh`
- `SHYFTY_DEV_BOOTSTRAP_ON_START=1 SHYFTY_DEV_BOOTSTRAP_DAYS_BACK=30 bash scripts/start-dev.sh`

`scripts/start-dev.sh` no longer seeds demo/sample rows. If bootstrap is enabled, it runs the real sync CLI before starting services and automatically includes `nfl` when `SPORTSDATAIO_NFL_API_KEY` is set.

## Product Scope

Kept:

- Signal feed
- Player and team pages that support the signal story
- Recent signal context and provenance
- Saved views and personalization

Deprioritized or being removed:

- Seed/demo workflows
- Fake NFL fallback data
- Deep basketball-reference-style history browsing
- Large game-log/archive surfaces that do not directly support signals

## Tests

- `cd backend && .venv/bin/python -m unittest discover -s tests -q`

Unit tests may still use small deterministic fixtures, but the runtime app path no longer depends on seed scripts or demo data.

## Current Gaps

- Scheduler currently runs a simple once-daily sync model.
- SportsDataIO integration is implemented against the documented weekly final feeds, but it still needs live-key validation in this repo environment.
- Additional source-specific checkpoints and incremental cursors can be layered onto the new sync tracking without redesigning the core flow.
