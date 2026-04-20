#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jackziegler/Projects/Shyfty"
BACKEND_DIR="$ROOT/backend"
WEB_DIR="$ROOT/web"
IOS_PROJECT="$ROOT/ios/Shyfty/Shyfty.xcodeproj"
SQLITE_DB="$ROOT/shyfty.db"

BACKEND_PORT=8001
WEB_PORT=5175
BACKEND_RELOAD="${BACKEND_RELOAD:-1}"
IPHONE_API_HOST="${SHYFTY_LAN_IP:-192.168.0.28}"
DEV_SEED_MODE="${SHYFTY_DEV_SEED_MODE:-auto}"
DEV_SEED_SEASON="${SHYFTY_DEV_SEED_SEASON:-}"
DEV_SEED_DAYS_BACK="${SHYFTY_DEV_SEED_DAYS_BACK:-21}"
DEV_SEED_MAX_GAMES="${SHYFTY_DEV_SEED_MAX_GAMES:-50}"
DEV_SEED_INCLUDE_NFL="${SHYFTY_DEV_SEED_INCLUDE_NFL:-1}"

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
  pids="$(lsof -ti tcp:"$port" || true)"
  if [[ -n "$pids" ]]; then
    echo "Killing processes on port $port: $pids"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
    pids="$(lsof -ti tcp:"$port" || true)"
    if [[ -n "$pids" ]]; then
      echo "Force killing processes on port $port: $pids"
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

echo "Cleaning up old dev processes..."
kill_pidfile "$ROOT/.run/backend.pid"
kill_pidfile "$ROOT/.run/web.pid"
kill_port "$BACKEND_PORT"
kill_port "$WEB_PORT"
rm -f "$ROOT/.run/seed.log"

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
  alembic upgrade head
)

current_stat_count() {
  source .venv/bin/activate
  python - <<'PY'
from sqlalchemy import inspect, text
from app.db.session import engine

with engine.connect() as conn:
    inspector = inspect(conn)
    if "player_game_stats" not in inspector.get_table_names():
        print(0)
    else:
        count = conn.execute(text("SELECT COUNT(*) FROM player_game_stats")).scalar_one()
        print(count)
PY
}

run_seed_if_needed() {
  local mode="$1"
  local stat_count=0
  local -a seed_args=("--generate-signals")

  case "$mode" in
    skip)
      echo "Skipping seed step because SHYFTY_DEV_SEED_MODE=skip."
      return
      ;;
    auto)
      stat_count="$(current_stat_count)"
      if [[ "$stat_count" -gt 0 ]]; then
        echo "Skipping seed step because existing stats were found ($stat_count rows)."
        return
      fi
      echo "Database is empty; running real NBA seed before startup."
      ;;
    real)
      echo "Running real NBA seed before startup."
      ;;
    demo)
      echo "Running demo seed before startup."
      seed_args+=("--demo-only")
      ;;
    *)
      echo "Unsupported SHYFTY_DEV_SEED_MODE=$mode"
      echo "Use one of: auto, real, demo, skip"
      exit 1
      ;;
  esac

  if [[ "$mode" != "demo" ]]; then
    if [[ -n "$DEV_SEED_SEASON" ]]; then
      seed_args+=("--season" "$DEV_SEED_SEASON")
    fi
    seed_args+=("--days-back" "$DEV_SEED_DAYS_BACK" "--max-games" "$DEV_SEED_MAX_GAMES")
    if [[ "$DEV_SEED_INCLUDE_NFL" != "1" ]]; then
      seed_args+=("--skip-nfl-demo")
    fi
  fi

  (
    source .venv/bin/activate
    python -m app.cli.seed_db "${seed_args[@]}"
  ) 2>&1 | tee "$ROOT/.run/seed.log"
}

run_seed_if_needed "$DEV_SEED_MODE"

nohup /bin/bash -lc "
  set -euo pipefail
  cd '$BACKEND_DIR'
  source .venv/bin/activate
  export DATABASE_URL='$DATABASE_URL'
  export WATCHFILES_FORCE_POLLING='${WATCHFILES_FORCE_POLLING:-true}'
  if [[ '$BACKEND_RELOAD' == '1' ]]; then
    exec uvicorn app.main:app --reload --host 0.0.0.0 --port '$BACKEND_PORT'
  else
    exec uvicorn app.main:app --host 0.0.0.0 --port '$BACKEND_PORT'
  fi
" > "$ROOT/.run/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$ROOT/.run/backend.pid"

sleep 2

echo "Starting React dev server on :$WEB_PORT ..."
cd "$WEB_DIR"
nohup /bin/bash -lc "
  set -euo pipefail
  cd '$WEB_DIR'
  exec npm run dev
" > "$ROOT/.run/web.log" 2>&1 &
WEB_PID=$!
echo "$WEB_PID" > "$ROOT/.run/web.pid"

sleep 2

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
