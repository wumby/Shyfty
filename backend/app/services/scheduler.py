"""Background scheduler that runs the NBA ingest pipeline daily at 3 AM UTC."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_ingest_task: Optional[asyncio.Task] = None

# Module-level ingest state — readable by the /ingest/status route
_ingest_state: dict = {
    "status": "idle",       # "idle" | "running" | "error"
    "last_updated": None,   # ISO string of last successful completion
    "started_at": None,     # ISO string
    "finished_at": None,    # ISO string
    "last_error": None,
    "recent_runs": [],
}


def get_ingest_state() -> dict:
    state = dict(_ingest_state)
    if state["status"] == "running" and state.get("started_at"):
        started_at = datetime.fromisoformat(state["started_at"])
        state["current_run_duration_seconds"] = max(0.0, (datetime.utcnow() - started_at).total_seconds())
    else:
        state["current_run_duration_seconds"] = None
    return state


async def run_ingest_once() -> None:
    """Run a full ingest, updating module state before/after. Safe to call from routes."""
    if _ingest_state["status"] == "running":
        logger.info("Scheduler: ingest already running, skipping trigger")
        return
    try:
        from app.services.ingest_pipeline import run_full_ingest

        run_record = {
            "started_at": datetime.utcnow().isoformat(),
            "finished_at": None,
            "status": "running",
            "duration_seconds": None,
            "error_message": None,
        }
        _ingest_state["status"] = "running"
        _ingest_state["started_at"] = run_record["started_at"]
        _ingest_state["finished_at"] = None
        _ingest_state["last_error"] = None
        logger.info("Scheduler: starting NBA ingest")

        result = await asyncio.to_thread(run_full_ingest, 21, 50)

        _ingest_state["status"] = "idle"
        _ingest_state["last_updated"] = datetime.utcnow().isoformat()
        _ingest_state["finished_at"] = _ingest_state["last_updated"]
        run_record["finished_at"] = _ingest_state["finished_at"]
        run_record["status"] = "success"
        run_record["duration_seconds"] = (
            datetime.fromisoformat(run_record["finished_at"]) - datetime.fromisoformat(run_record["started_at"])
        ).total_seconds()
        _ingest_state["recent_runs"] = [run_record, *_ingest_state["recent_runs"]][:12]
        logger.info(
            "Scheduler: ingest complete — games=%d players=%d signals_created=%d",
            result.games_fetched,
            result.players_loaded,
            result.signals_created,
        )
    except Exception:
        _ingest_state["status"] = "error"
        _ingest_state["finished_at"] = datetime.utcnow().isoformat()
        _ingest_state["last_error"] = "The latest ingest run failed. Review the recent run log for details."
        _ingest_state["recent_runs"] = [
            {
                "started_at": _ingest_state["started_at"] or datetime.utcnow().isoformat(),
                "finished_at": _ingest_state["finished_at"],
                "status": "failed",
                "duration_seconds": (
                    datetime.fromisoformat(_ingest_state["finished_at"]) - datetime.fromisoformat(_ingest_state["started_at"])
                ).total_seconds() if _ingest_state.get("started_at") else None,
                "error_message": _ingest_state["last_error"],
            },
            *_ingest_state["recent_runs"],
        ][:12]
        logger.exception("Scheduler: ingest failed")


async def _daily_loop() -> None:
    while True:
        delay = await _next_run_delay()
        logger.info("Scheduler: next ingest in %.0f seconds (%.1f hours)", delay, delay / 3600)
        await asyncio.sleep(delay)
        await run_ingest_once()


async def _next_run_delay() -> float:
    now = datetime.utcnow()
    target = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def start_scheduler() -> None:
    global _ingest_task
    _ingest_task = asyncio.create_task(_daily_loop())
    logger.info("Scheduler: daily ingest task started")


def stop_scheduler() -> None:
    global _ingest_task
    if _ingest_task is not None:
        _ingest_task.cancel()
        _ingest_task = None
        logger.info("Scheduler: daily ingest task stopped")
