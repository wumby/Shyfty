from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.reaction import ReactionSummaryRead, ReactionType


class SignalSummaryTemplateInputs(BaseModel):
    current_value: float
    baseline_value: float
    movement_pct: Optional[float]
    baseline_window: str
    trend_direction: str


class SignalRead(BaseModel):
    id: int
    player_id: int
    game_id: int
    player_name: str
    team_name: str
    league_name: str
    signal_type: str
    metric_name: str
    current_value: float
    baseline_value: float
    z_score: float
    explanation: str
    importance: float
    importance_label: str
    baseline_window: str
    baseline_window_size: int
    event_date: date
    movement_pct: Optional[float]
    metric_label: str
    trend_direction: str
    rolling_stddev: float
    classification_reason: str
    summary_template: str
    summary_template_inputs: SignalSummaryTemplateInputs
    reaction_summary: ReactionSummaryRead
    user_reaction: Optional[ReactionType]
    created_at: datetime


class BaselineSampleRead(BaseModel):
    stat_id: int
    game_id: int
    game_date: date
    value: float
    source_system: Optional[str]
    source_game_id: Optional[str]
    source_player_id: Optional[str]
    raw_snapshot_path: Optional[str]
    raw_payload_path: Optional[str]
    raw_record_index: Optional[int]


class SourceStatContextRead(BaseModel):
    stat_id: int
    game_id: int
    game_date: date
    metric_name: str
    current_value: float
    raw_stats: dict[str, float]
    source_system: Optional[str]
    source_game_id: Optional[str]
    source_player_id: Optional[str]
    raw_snapshot_path: Optional[str]
    raw_payload_path: Optional[str]
    raw_record_index: Optional[int]


class RollingMetricTraceRead(BaseModel):
    id: Optional[int]
    player_id: int
    game_id: int
    metric_name: str
    source_stat_id: Optional[int]
    rolling_avg: float
    rolling_stddev: float
    z_score: float


class SignalTraceRead(BaseModel):
    signal: SignalRead
    rolling_metric: RollingMetricTraceRead
    source_stat: SourceStatContextRead
    baseline_samples: list[BaselineSampleRead]


class PaginatedSignals(BaseModel):
    items: list[SignalRead]
    has_more: bool
    next_cursor: Optional[int]
