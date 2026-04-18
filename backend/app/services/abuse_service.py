from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

_WINDOWS: dict[tuple[str, str], deque[datetime]] = defaultdict(deque)


def enforce_rate_limit(subject: str, action: str, limit: int, per_seconds: int) -> None:
    now = datetime.now(timezone.utc)
    key = (subject, action)
    window = _WINDOWS[key]
    cutoff = now - timedelta(seconds=per_seconds)
    while window and window[0] < cutoff:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many {action.replace('_', ' ')} attempts. Slow down and try again shortly.",
        )
    window.append(now)
