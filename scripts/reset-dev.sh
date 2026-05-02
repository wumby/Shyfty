#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jackziegler/Projects/Shyfty"
BACKEND_DIR="$ROOT/backend"
WEB_DIR="$ROOT/web"
IOS_PROJECT="$ROOT/ios/Shyfty/Shyfty.xcodeproj"
SQLITE_DB="$ROOT/shyfty.db"

BACKEND_PORT=8001
WEB_PORT=5175
BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_RELOAD="${BACKEND_RELOAD:-1}"
DEV_FOREGROUND="${DEV_FOREGROUND:-0}"
IPHONE_API_HOST="${SHYFTY_LAN_IP:-192.168.0.28}"
DEV_SYNC_MAX_GAMES="${DEV_SYNC_MAX_GAMES:-260}"
DEV_MIN_GAMES_PER_TEAM="${DEV_MIN_GAMES_PER_TEAM:-5}"

detect_lan_ip() {
  if [[ -n "${SHYFTY_LAN_IP:-}" ]]; then
    printf '%s\n' "$SHYFTY_LAN_IP"
    return
  fi

  local candidate=""
  for iface in en0 en1; do
    candidate="$(ipconfig getifaddr "$iface" 2>/dev/null || true)"
    if [[ -n "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
}


kill_pidfile() {
  local pidfile="$1"
  if [[ ! -f "$pidfile" ]]; then
    return
  fi

  local pid
  pid="$(tr -d '[:space:]' < "$pidfile")"
  if [[ -z "$pid" ]]; then
    rm -f "$pidfile"
    return
  fi

  if kill -0 "$pid" >/dev/null 2>&1; then
    echo "Killing process from $pidfile: $pid"
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Force killing process from $pidfile: $pid"
      kill -9 "$pid" >/dev/null 2>&1 || true
    fi
  fi

  rm -f "$pidfile"
}

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN || true)"
  if [[ -n "$pids" ]]; then
    echo "Killing listening processes on port $port: $pids"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
    pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN || true)"
    if [[ -n "$pids" ]]; then
      echo "Force killing listening processes on port $port: $pids"
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

ensure_pid_running() {
  local pid="$1"
  local name="$2"
  local logfile="$3"
  if ! kill -0 "$pid" >/dev/null 2>&1; then
    echo "$name exited during startup. Recent log:"
    tail -80 "$logfile" 2>/dev/null || true
    exit 1
  fi
}

wait_for_listen() {
  local port="$1"
  local name="$2"
  local logfile="$3"
  local attempts=30
  local attempt=1

  while (( attempt <= attempts )); do
    if lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    attempt=$((attempt + 1))
  done

  echo "$name did not start listening on port $port. Recent log:"
  tail -80 "$logfile" 2>/dev/null || true
  exit 1
}

wait_for_http() {
  local url="$1"
  local name="$2"
  local logfile="$3"
  local attempts=30
  local attempt=1

  while (( attempt <= attempts )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
    attempt=$((attempt + 1))
  done

  echo "$name did not become healthy at $url. Recent log:"
  tail -80 "$logfile" 2>/dev/null || true
  exit 1
}

cleanup_started_processes() {
  if [[ -n "${WEB_PID:-}" ]] && kill -0 "$WEB_PID" >/dev/null 2>&1; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "${BACKEND_PID:-}" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

echo "Cleaning up old dev processes..."
kill_pidfile "$ROOT/.run/backend.pid"
kill_pidfile "$ROOT/.run/web.pid"
kill_pidfile "$ROOT/.run/sync.pid"
kill_port "$BACKEND_PORT"
kill_port "$WEB_PORT"
rm -f "$ROOT/.run/sync.log"

mkdir -p "$ROOT/.run"

LAN_IP="$(detect_lan_ip || true)"
LOCAL_API_URL="http://127.0.0.1:$BACKEND_PORT/api"
DETECTED_API_URL=""
if [[ -n "$LAN_IP" ]]; then
  DETECTED_API_URL="http://$LAN_IP:$BACKEND_PORT/api"
fi
IPHONE_API_URL="http://$IPHONE_API_HOST:$BACKEND_PORT/api"

echo "Starting backend on :$BACKEND_PORT ..."
cd "$BACKEND_DIR"
if [[ ! -d ".venv" ]]; then
  echo "Missing backend virtualenv at $BACKEND_DIR/.venv"
  echo "Create it first:"
  echo "  cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi

if [[ -z "${DATABASE_URL:-}" ]]; then
  if [[ -f "$SQLITE_DB" ]]; then
    export DATABASE_URL="sqlite:///$SQLITE_DB"
  else
    export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/shyfty"
  fi
fi

echo "Using backend database: $DATABASE_URL"

run_alembic_upgrade_with_retry() {
  local attempts=5
  local delay_seconds=2
  local attempt=1

  while (( attempt <= attempts )); do
    if alembic upgrade head; then
      return 0
    fi

    if [[ "$DATABASE_URL" != sqlite:///* ]] || (( attempt == attempts )); then
      return 1
    fi

    echo "SQLite migration hit a lock; retrying in ${delay_seconds}s (${attempt}/${attempts})..."
    sleep "$delay_seconds"
    attempt=$((attempt + 1))
  done
}

echo "Applying backend migrations..."
(
  source .venv/bin/activate
  if [[ "$DATABASE_URL" == sqlite:///* ]] && [[ -f "$SQLITE_DB" ]]; then
    has_tables="$(sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")"
    has_alembic_version="$(sqlite3 "$SQLITE_DB" "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='alembic_version';")"
    if [[ "$has_tables" -gt 0 && "$has_alembic_version" -eq 0 ]]; then
      echo "Stamping legacy SQLite database at 0001_initial before upgrade..."
      alembic stamp 0001_initial
    fi
  fi
  run_alembic_upgrade_with_retry
)

echo "Starting data sync in background (NBA + NFL)..."
nohup /bin/bash -lc "
  set -euo pipefail
  cd '$ROOT'
  export DATABASE_URL='$DATABASE_URL'
  bash scripts/bootstrap-min-coverage.sh --min-games-per-team '$DEV_MIN_GAMES_PER_TEAM' --max-games '$DEV_SYNC_MAX_GAMES'
" > "$ROOT/.run/sync.log" 2>&1 &
SYNC_PID=$!
echo "$SYNC_PID" > "$ROOT/.run/sync.pid"
echo "Sync PID $SYNC_PID running in background. Follow: tail -f $ROOT/.run/sync.log"

nohup /bin/bash -lc "
  set -euo pipefail
  cd '$BACKEND_DIR'
  source .venv/bin/activate
  export DATABASE_URL='$DATABASE_URL'
  export WATCHFILES_FORCE_POLLING='${WATCHFILES_FORCE_POLLING:-true}'
  if [[ '$BACKEND_RELOAD' == '1' ]]; then
    exec uvicorn app.main:app --reload --host '$BACKEND_HOST' --port '$BACKEND_PORT'
  else
    exec uvicorn app.main:app --host '$BACKEND_HOST' --port '$BACKEND_PORT'
  fi
" > "$ROOT/.run/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$ROOT/.run/backend.pid"

ensure_pid_running "$BACKEND_PID" "Backend" "$ROOT/.run/backend.log"
wait_for_listen "$BACKEND_PORT" "Backend" "$ROOT/.run/backend.log"
wait_for_http "$LOCAL_API_URL/health" "Backend" "$ROOT/.run/backend.log"

echo "Starting React dev server on :$WEB_PORT ..."
cd "$WEB_DIR"
nohup /bin/bash -lc "
  set -euo pipefail
  cd '$WEB_DIR'
  exec npm run dev
" > "$ROOT/.run/web.log" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$ROOT/.run/web.pid"

ensure_pid_running "$WEB_PID" "Web server" "$ROOT/.run/web.log"
wait_for_listen "$WEB_PORT" "Web server" "$ROOT/.run/web.log"

if [[ "${OPEN_IOS_PROJECT:-1}" == "1" ]]; then
  if command -v open >/dev/null 2>&1; then
    echo "Opening iOS project..."
    open -a Xcode "$IOS_PROJECT" || echo "Could not open iOS project automatically. Open it manually in Xcode if needed."
  else
    echo "Skipping iOS project open because 'open' is unavailable."
  fi
else
  echo "Skipping iOS project open because OPEN_IOS_PROJECT=$OPEN_IOS_PROJECT."
fi

echo
echo "Started:"
echo "  Backend (simulator/web): $LOCAL_API_URL"
echo "  Backend (iPhone/Wi-Fi): $IPHONE_API_URL"
echo "  Web:     http://localhost:$WEB_PORT"
if [[ -n "$DETECTED_API_URL" ]] && [[ "$DETECTED_API_URL" != "$IPHONE_API_URL" ]]; then
  echo
  echo "Detected LAN API URL differs from the iPhone app setting:"
  echo "  detected: $DETECTED_API_URL"
  echo "  iPhone:   $IPHONE_API_URL"
  echo "Set SHYFTY_LAN_IP to override the printed iPhone URL if your Mac IP changes."
fi
echo
echo "Logs:"
echo "  tail -f $ROOT/.run/backend.log"
echo "  tail -f $ROOT/.run/web.log"

if [[ "$DEV_FOREGROUND" == "1" ]]; then
  echo
  echo "DEV_FOREGROUND=1; keeping backend and web attached. Press Ctrl+C to stop."
  trap cleanup_started_processes INT TERM EXIT
  wait "$BACKEND_PID" "$WEB_PID"
fi
