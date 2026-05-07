from app.services import shyft_generation_service as _shyft_generation_service
from app.services.shyft_generation_service import (
    ShyftGenerationError as SignalGenerationError,
    ShyftGenerationResult as SignalGenerationResult,
    _upsert_rolling_metric,
    build_shyft_generation_context,
)

build_signal_generation_context = build_shyft_generation_context


def generate_signals(db):
    original = _shyft_generation_service._upsert_rolling_metric
    _shyft_generation_service._upsert_rolling_metric = _upsert_rolling_metric
    try:
        return _shyft_generation_service.generate_shyfts(db)
    finally:
        _shyft_generation_service._upsert_rolling_metric = original


def generate_signals_for_players(db, player_ids, *, team_ids=None):
    return _shyft_generation_service.generate_shyfts_for_players(db, player_ids, team_ids=team_ids)
