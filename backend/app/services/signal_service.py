from typing import Optional

from sqlalchemy.orm import Session

from app.services.shyft_service import (
    FEED_MODE_ALL,
    FEED_MODE_FOLLOWING,
    FEED_MODE_FOR_YOU,
    SORT_MODE_DEVIATION,
    SORT_MODE_DISCUSSED,
    SORT_MODE_IMPORTANT,
    SORT_MODE_NEWEST,
    _apply_sort,
    _base_shyft_query,
    _build_shyft_items,
    detect_cascade_shyfts,
    list_shyfts,
)

_base_signal_query = _base_shyft_query
_build_signal_items = _build_shyft_items
detect_cascade_signals = detect_cascade_shyfts


def list_signals(
    db: Session,
    league: Optional[str],
    team: Optional[str],
    player: Optional[str],
    signal_type: Optional[str],
    limit: int = 24,
    before_id: Optional[int] = None,
    current_user_id: Optional[int] = None,
    sort_mode: str = SORT_MODE_NEWEST,
    feed_mode: str = FEED_MODE_ALL,
    date_from=None,
    date_to=None,
):
    return list_shyfts(
        db=db,
        league=league,
        team=team,
        player=player,
        shyft_type=signal_type,
        limit=limit,
        before_id=before_id,
        current_user_id=current_user_id,
        sort_mode=sort_mode,
        feed_mode=feed_mode,
        date_from=date_from,
        date_to=date_to,
    )

