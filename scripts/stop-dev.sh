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

echo "Stopping dev services..."
kill_pidfile "$ROOT/.run/backend.pid"
kill_pidfile "$ROOT/.run/web.pid"
kill_port "$BACKEND_PORT"
kill_port "$WEB_PORT"
rm -f "$ROOT/.run/seed.log"

echo "Stopped backend on :$BACKEND_PORT and web on :$WEB_PORT."
