from pathlib import Path

# Package alias for commands run from repo root, e.g.:
# python -m backend.app.ingest.cli
__path__ = [str(Path(__file__).resolve().parents[1] / "backend" / "app")]
