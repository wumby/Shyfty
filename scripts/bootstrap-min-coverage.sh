#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$BACKEND_DIR" \
"$BACKEND_DIR/.venv/bin/python" -m app.cli.bootstrap_min_coverage "$@"
