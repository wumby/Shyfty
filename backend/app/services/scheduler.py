"""Background scheduler that runs the NBA ingest pipeline daily at 3 AM UTC."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

_ingest_task: Optional[asyncio.Task] = None

# Module-level ingest state — readable by the /ingest/status route.
# Seeded from DB on startup so freshness survives server restarts.
_ingest_state: dict = {
    "status": "idle",
    "last_updated": None,
    "started_at": None,
    "finished_at": None,
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


def _load_state_from_db() -> None:
    """Seed _ingest_state from the last IngestRun rows so freshness survives restarts."""
    global _ingest_state
    try:
        from sqlalchemy import desc, select
        from app.db.session import SessionLocal
        from app.models.ingest_run import IngestRun

        db = SessionLocal()
        try:
            last_success = db.execute(
                select(IngestRun)
                .where(IngestRun.status == "success")
                .order_by(desc(IngestRun.finished_at))
                .limit(1)
            ).scalar_one_or_none()

            recent = db.execute(
                select(IngestRun).order_by(desc(IngestRun.started_at)).limit(12)
            ).scalars().all()

            if last_success:
                _ingest_state["status"] = "idle"
                _ingest_state["last_updated"] = last_success.finished_at.isoformat() if last_success.finished_at else None
                _ingest_state["started_at"] = last_success.started_at.isoformat() if last_success.started_at else None
                _ingest_state["finished_at"] = last_success.finished_at.isoformat() if last_success.finished_at else None
                _ingest_state["last_error"] = None

            _ingest_state["recent_runs"] = [
                {
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                    "status": run.status,
                    "duration_seconds": run.duration_seconds,
                    "error_message": run.error_message,
                }
                for run in recent
            ]
        finally:
            db.close()
    except Exception:
        logger.warning("Could not seed ingest state from DB — freshness will show unknown until first run", exc_info=True)


def _persist_run_start(started_at: str) -> Optional[int]:
    try:
        from app.db.session import SessionLocal
        from app.models.ingest_run import IngestRun

        db = SessionLocal()
        try:
            run = IngestRun(started_at=datetime.fromisoformat(started_at), status="running")
            db.add(run)
            db.commit()
            db.refresh(run)
            return run.id
        finally:
            db.close()
    except Exception:
        logger.warning("Could not persist ingest run start to DB", exc_info=True)
        return None


def _persist_run_finish(
    run_id: Optional[int],
    status: str,
    result,
    error_message: Optional[str],
    started_at: str,
    finished_at: str,
) -> None:
    try:
        from app.db.session import SessionLocal
        from app.models.ingest_run import IngestRun

        db = SessionLocal()
        try:
            if run_id is not None:
                run = db.get(IngestRun, run_id)
                if run:
                    run.status = status
                    run.finished_at = datetime.fromisoformat(finished_at)
                    run.error_message = error_message
                    if result is not None:
                        run.games_fetched = result.games_fetched
                        run.players_loaded = result.players_loaded
                        run.signals_created = result.signals_created
                        run.signals_updated = result.signals_updated
                    run.duration_seconds = (
                        datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
                    ).total_seconds()
                    db.commit()
        finally:
            db.close()
    except Exception:
        logger.warning("Could not persist ingest run finish to DB", exc_info=True)


async def run_ingest_once() -> None:
    """Run a full ingest, updating module state and DB before/after. Safe to call from routes."""
    if _ingest_state["status"] == "running":
        logger.info("Scheduler: ingest already running, skipping trigger")
        return
    try:
        from app.services.ingest_pipeline import run_full_ingest

        started_at = datetime.utcnow().isoformat()
        _ingest_state["status"] = "running"
        _ingest_state["started_at"] = started_at
        _ingest_state["finished_at"] = None
        _ingest_state["last_error"] = None
        logger.info("Scheduler: starting NBA ingest")

        run_id = await asyncio.to_thread(_persist_run_start, started_at)

        result = await asyncio.to_thread(run_full_ingest, 21, 50)

        finished_at = datetime.utcnow().isoformat()
        _ingest_state["status"] = "idle"
        _ingest_state["last_updated"] = finished_at
        _ingest_state["finished_at"] = finished_at

        run_record = {
            "started_at": started_at,
            "finished_at": finished_at,
            "status": "success",
            "duration_seconds": (
                datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
            ).total_seconds(),
            "error_message": None,
        }
        _ingest_state["recent_runs"] = [run_record, *_ingest_state["recent_runs"]][:12]

        await asyncio.to_thread(_persist_run_finish, run_id, "success", result, None, started_at, finished_at)

        logger.info(
            "Scheduler: ingest complete — games=%d players=%d signals_created=%d",
            result.games_fetched,
            result.players_loaded,
            result.signals_created,
        )
    except Exception:
        finished_at = datetime.utcnow().isoformat()
        error_message = "The latest ingest run failed. Review the recent run log for details."
        started_at = _ingest_state.get("started_at") or finished_at
        _ingest_state["status"] = "error"
        _ingest_state["finished_at"] = finished_at
        _ingest_state["last_error"] = error_message
        _ingest_state["recent_runs"] = [
            {
                "started_at": started_at,
                "finished_at": finished_at,
                "status": "failed",
                "duration_seconds": (
                    datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)
                ).total_seconds(),
                "error_message": error_message,
            },
            *_ingest_state["recent_runs"],
        ][:12]

        run_id = None  # may not have been persisted if start failed
        await asyncio.to_thread(_persist_run_finish, run_id, "failed", None, error_message, started_at, finished_at)
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
    _load_state_from_db()
    _ingest_task = asyncio.create_task(_daily_loop())
    logger.info("Scheduler: daily ingest task started")


def stop_scheduler() -> None:
    global _ingest_task
    if _ingest_task is not None:
        _ingest_task.cancel()
        _ingest_task = None
        logger.info("Scheduler: daily ingest task stopped")
