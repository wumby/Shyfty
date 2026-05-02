#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

PYTHONDONTWRITEBYTECODE=1 \
PYTHONPATH="$ROOT_DIR/backend" \
"$ROOT_DIR/backend/.venv/bin/python" -m unittest discover -s "$ROOT_DIR/backend/tests" -p "test_*.py"
