from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.comment import CommentRead
from app.schemas.reaction import ReactionSummaryRead, ReactionType


class IngestRunRead(BaseModel):
    started_at: str
    finished_at: Optional[str] = None
    status: str
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None


class IngestStatusRead(BaseModel):
    status: str  # "idle" | "running" | "error"
    last_updated: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    current_run_duration_seconds: Optional[float] = None
    last_error: Optional[str] = None
    recent_runs: list[IngestRunRead] = []


class FeedContextRead(BaseModel):
    feed_mode: str
    sort_mode: str
    personalization_reason: Optional[str] = None


class FreshnessContextRead(BaseModel):
    state: str
    label: str
    coverage_summary: str
    delayed_data_message: Optional[str] = None
    ingest_age_minutes: Optional[int] = None
    event_age_hours: Optional[int] = None


class SignalSummaryTemplateInputs(BaseModel):
    current_value: float
    baseline_value: float
    movement_pct: Optional[float]
    baseline_window: str
    trend_direction: str
    medium_window_z: Optional[float] = None
    season_window_z: Optional[float] = None
    trend_slope: Optional[float] = None
    usage_shift: Optional[float] = None


class WindowContextRead(BaseModel):
    sample_size: int
    values: list[float]
    rolling_avg: float
    rolling_stddev: float
    z_score: float


class SignalRead(BaseModel):
    id: int
    subject_type: str = "player"
    player_id: Optional[int] = None
    team_id: int
    game_id: int
    player_name: str
    team_name: str
    league_name: str
    signal_type: str
    metric_name: str
    current_value: float
    baseline_value: float
    z_score: float
    signal_score: float
    score_explanation: Optional[str] = None
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
    opponent: Optional[str] = None
    home_away: Optional[str] = None
    game_result: Optional[str] = None
    final_score: Optional[str] = None
    classification_reason: str
    summary_template: str
    summary_template_inputs: SignalSummaryTemplateInputs
    narrative_summary: Optional[str] = None
    reaction_summary: ReactionSummaryRead
    user_reaction: Optional[ReactionType]
    comment_count: int = 0
    is_favorited: bool = False
    created_at: datetime
    freshness: Optional[FreshnessContextRead] = None


class BaselineSampleRead(BaseModel):
    stat_id: int
    game_id: int
    game_date: date
    value: float
    source_system: Optional[str]
    source_game_id: Optional[str]
    source_player_id: Optional[str] = None
    source_team_id: Optional[str] = None
    raw_snapshot_path: Optional[str]
    raw_payload_path: Optional[str]
    raw_advanced_payload_path: Optional[str] = None
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
    source_player_id: Optional[str] = None
    source_team_id: Optional[str] = None
    raw_snapshot_path: Optional[str]
    raw_payload_path: Optional[str]
    raw_advanced_payload_path: Optional[str] = None
    raw_record_index: Optional[int]


class RollingMetricTraceRead(BaseModel):
    id: Optional[int]
    player_id: Optional[int] = None
    game_id: int
    metric_name: str
    source_stat_id: Optional[int]
    rolling_avg: float
    rolling_stddev: float
    z_score: float
    short_window: WindowContextRead
    medium_window: WindowContextRead
    season_window: WindowContextRead
    ewma: Optional[float] = None
    recent_delta: Optional[float] = None
    trend_slope: Optional[float] = None
    volatility_index: Optional[float] = None
    volatility_delta: Optional[float] = None
    opponent_average_allowed: Optional[float] = None
    opponent_rank: Optional[int] = None
    pace_proxy: Optional[float] = None
    usage_shift: Optional[float] = None
    high_volatility: Optional[bool] = None


class SignalTraceRead(BaseModel):
    signal: SignalRead
    rolling_metric: RollingMetricTraceRead
    source_stat: SourceStatContextRead
    baseline_samples: list[BaselineSampleRead]
    discussion_preview: list[CommentRead] = []
    related_signals: list[SignalRead] = []
    feed_context: Optional[FeedContextRead] = None


class PaginatedSignals(BaseModel):
    items: list[SignalRead]
    has_more: bool
    next_cursor: Optional[int]
    feed_context: Optional[FeedContextRead] = None
