"""Background scheduler that runs the NBA ingest pipeline daily at 3 AM UTC."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_ingest_task: asyncio.Task | None = None


async def _next_run_delay() -> float:
    now = datetime.utcnow()
    target = now.replace(hour=3, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    delay = (target - now).total_seconds()
    return delay


async def _run_ingest_once() -> None:
    try:
        from app.services.ingest_pipeline import run_full_ingest

        logger.info("Scheduler: starting daily NBA ingest")
        result = run_full_ingest(days_back=21, max_games=30)
        logger.info(
            "Scheduler: ingest complete — games=%d players=%d signals_created=%d",
            result.games_fetched,
            result.players_loaded,
            result.signals_created,
        )
    except Exception:
        logger.exception("Scheduler: ingest failed")


async def _daily_loop() -> None:
    while True:
        delay = await _next_run_delay()
        logger.info("Scheduler: next ingest in %.0f seconds (%.1f hours)", delay, delay / 3600)
        await asyncio.sleep(delay)
        await _run_ingest_once()


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
