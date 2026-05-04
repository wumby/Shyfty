# Shyfty Production Deployment (Railway)

This runbook targets a cheap production setup with split hosting:
- `web/` deployed as static assets
- `backend/` deployed as a containerized FastAPI service
- managed PostgreSQL
- ingest run as a separate scheduled job

## Required Environment Variables

Backend:
- `APP_ENV=production`
- `PORT` (Railway sets this automatically)
- `DATABASE_URL=postgresql+psycopg://...`
- `FRONTEND_ORIGIN=https://your-frontend-domain.com`
- `API_PUBLIC_URL=https://your-backend-domain.com`
- `TRUST_PROXY_HEADERS=true`
- `ALLOWED_HOSTS=your-backend-domain.com`
- `CORS_ORIGINS=https://your-frontend-domain.com` (comma-separated for multiple)
- `SESSION_SECRET` (strong random string)
- `JWT_SECRET` (strong random string)
- `AUTH_COOKIE_SECURE=true`
- `CSRF_COOKIE_SECURE=true`
- `AUTH_COOKIE_SAMESITE=none`
- `CSRF_COOKIE_SAMESITE=none`
- `SYNC_SCHEDULER_ENABLED=false`
- `SYNC_RUN_ON_STARTUP=false`
- `ENABLE_NBA_SYNC=true`
- `ENABLE_NFL_SYNC=false` (until NFL provider is finalized)
- `SYNC_LOOKBACK_DAYS=1`
- `SYNC_LOOKAHEAD_DAYS=1`
- `STAT_CORRECTION_LOOKBACK_HOURS=48`

Frontend:
- `VITE_API_BASE_URL=https://your-backend-domain.com/api`

## Backend Service (Railway)

1. Create a new Railway service from this repo.
2. Set root directory to `backend/`.
3. Build command:
   - `pip install --no-cache-dir -r requirements.txt`
4. Start command:
   - `alembic upgrade head && gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY:-2} --access-logfile - --error-logfile -`
5. Add all backend env vars listed above.

Health check URL:
- `https://<backend-domain>/api/health`

## PostgreSQL Setup

1. Add Railway PostgreSQL.
2. Copy the generated connection string into backend `DATABASE_URL`.
3. Run migrations:
   - via start command above (automatic on deploy), or
   - one-off shell command: `alembic upgrade head`

## Frontend Static Deployment

Use any static host (Railway static, Netlify, Vercel static output, Cloudflare Pages).

1. Build from `web/`:
   - `npm ci`
   - `npm run build`
2. Publish `web/dist`.
3. Set `VITE_API_BASE_URL` before build.

Example file: [web/.env.production.example](/Users/jackziegler/Projects/Shyfty/web/.env.production.example:1)

## CORS and Cookie Settings

For split frontend/backend domains:
- `FRONTEND_ORIGIN` should be the exact web app origin.
- `API_PUBLIC_URL` should be the public backend URL.
- `CORS_ORIGINS` must include the exact frontend origin(s) (or leave unset and rely on `FRONTEND_ORIGIN`).
- `ALLOWED_HOSTS` must include the backend host Railway routes to (and any custom domain).
- Keep `AUTH_COOKIE_SECURE=true` and `CSRF_COOKIE_SECURE=true`.
- For split domains, cookie SameSite is automatically hardened to `none` when needed.
- Frontend already sends `credentials: include`.

## Railway Proxy Behavior

Railway terminates TLS before traffic reaches your container. Set:
- `TRUST_PROXY_HEADERS=true` so forwarded proto/host headers are honored.
- `AUTH_COOKIE_SECURE=true` and `CSRF_COOKIE_SECURE=true` so cookies are only sent over HTTPS.

With trusted proxy headers enabled, backend request context correctly reflects HTTPS/public host behind Railway’s proxy layer.

## Scheduled Ingest Job

Do not run heavy ingest in API startup. Use a separate scheduled command:

- `python -m app.ingest.cli sync --all`

Railway option:
1. Create a separate service/job using the same `backend/` root.
2. Reuse `DATABASE_URL`, `SESSION_SECRET`, `JWT_SECRET`, `APP_ENV=production`.
3. Configure a cron schedule (for example every 6-24 hours).

Manual one-off ingest:
- `python -m app.ingest.cli sync --league NBA --from YYYY-MM-DD --to YYYY-MM-DD`
- `python -m app.ingest.cli sync --league NBA --from YYYY-MM-DD --to YYYY-MM-DD --force`

## Idempotency Notes

Ingest reruns are idempotent by design:
- raw ingest events are deduplicated by `(source, external_id)` before insert
- signals are constrained by unique generation context
- reactions are constrained to avoid duplicate user/signal/type rows
- schedule-first sync hydrates only games that need refresh, which is cheaper on API quotas than broad re-fetches.

## Local Production-Like Test (Docker Compose)

Use: [infra/docker-compose.prod.yml](/Users/jackziegler/Projects/Shyfty/infra/docker-compose.prod.yml:1)

1. Create env values:
   - `export POSTGRES_PASSWORD=...`
   - `export SESSION_SECRET=...`
   - `export JWT_SECRET=...`
   - `export CORS_ORIGINS=https://your-frontend-domain.com`
2. Start:
   - `docker compose -f infra/docker-compose.prod.yml up --build`
3. Run one-off ingest:
   - `docker compose -f infra/docker-compose.prod.yml --profile ops run --rm ingest`
4. Verify health:
   - `curl -s http://127.0.0.1:8001/api/health`

## Rollback Notes

1. Keep previous Railway deployment artifact/version available.
2. If app rollback is needed without schema change, redeploy previous version.
3. If a migration causes issues:
   - stop new writes
   - run `alembic downgrade -1` only when the migration is confirmed reversible
   - redeploy previous backend version
4. Always validate `/api/health` and a signed-in request flow after rollback.
