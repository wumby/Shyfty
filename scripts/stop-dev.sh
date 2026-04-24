#!/usr/bin/env bash
set -euo pipefail

ROOT="/Users/jackziegler/Projects/Shyfty"
BACKEND_PORT=8001
WEB_PORT=5175

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
    echo "Stopping process from $pidfile: $pid"
    kill "$pid" >/dev/null 2>&1 || true
    sleep 1
    if kill -0 "$pid" >/dev/null 2>&1; then
      echo "Force stopping process from $pidfile: $pid"
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
    echo "Stopping processes on port $port: $pids"
    kill $pids >/dev/null 2>&1 || true
    sleep 1
    pids="$(lsof -ti tcp:"$port" || true)"
    if [[ -n "$pids" ]]; then
      echo "Force stopping processes on port $port: $pids"
      kill -9 $pids >/dev/null 2>&1 || true
    fi
  fi
}

BACKEND_DIR="$ROOT/backend"
SQLITE_DB="$ROOT/shyfty.db"

echo "Stopping dev services..."
kill_pidfile "$ROOT/.run/backend.pid"
kill_pidfile "$ROOT/.run/web.pid"
kill_port "$BACKEND_PORT"
kill_port "$WEB_PORT"
rm -f "$ROOT/.run/sync.log"

echo "Stopped backend on :$BACKEND_PORT and web on :$WEB_PORT."

if [[ -f "$BACKEND_DIR/.venv/bin/activate" ]]; then
  if [[ -z "${DATABASE_URL:-}" ]]; then
    if [[ -f "$SQLITE_DB" ]]; then
      export DATABASE_URL="sqlite:///$SQLITE_DB"
    else
      export DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/shyfty"
    fi
  fi

  echo "Resetting sports data..."
  (
    cd "$BACKEND_DIR"
    source .venv/bin/activate
    python -m app.cli.reset_data --mode sports-data
  ) || echo "Data reset skipped (DB may already be empty)."
fi
