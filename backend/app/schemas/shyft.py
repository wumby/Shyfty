from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel

from app.schemas.comment import CommentRead
from app.schemas.reaction import ReactionAggregateRead, ReactionSummaryRead, ReactionType


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


class ShyftSummaryTemplateInputs(BaseModel):
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


class ShyftDebugTraceRead(BaseModel):
    baseline: float
    actual: float
    delta: float
    z_score: float
    sample_size: int
    thresholds: dict[str, Union[float, int, None]]
    conditions: dict[str, bool]
    passed: bool


class ShyftRead(BaseModel):
    type: Literal["shyft"] = "shyft"
    id: int
    subject_type: str = "player"
    player_id: Optional[int] = None
    team_id: int
    game_id: int
    player_name: str
    team_name: str
    league_name: str
    shyft_type: str
    severity: str
    metric_name: str
    current_value: float
    baseline_value: float
    performance: Optional[float] = None
    deviation: Optional[float] = None
    z_score: float
    shyft_score: float
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
    debug_trace: ShyftDebugTraceRead
    summary_template: str
    summary_template_inputs: ShyftSummaryTemplateInputs
    narrative_summary: Optional[str] = None
    streak: int = 1
    reaction_summary: ReactionSummaryRead
    user_reaction: Optional[ReactionType]
    reactions: list[ReactionAggregateRead] = []
    user_reactions: list[ReactionType] = []
    comment_count: int = 0
    created_at: datetime


class CascadePlayerRead(BaseModel):
    id: Optional[int] = None
    name: str


class CascadeTriggerRead(BaseModel):
    player: CascadePlayerRead
    shyft_id: int
    stat: str
    metric_label: str
    delta: float
    delta_percent: Optional[float] = None
    shyft_type: str
    shyft_score: float


class CascadeContributorRead(BaseModel):
    player: CascadePlayerRead
    shyft_id: int
    stat: str
    metric_label: str
    delta: float
    delta_percent: Optional[float] = None
    shyft_type: str
    shyft_score: float


class CascadeShyftRead(BaseModel):
    type: Literal["cascade"] = "cascade"
    id: str
    game_id: int
    team_id: int
    team: str
    league_name: str
    game_date: date
    created_at: datetime
    trigger: CascadeTriggerRead
    contributors: list[CascadeContributorRead]
    underlying_shyfts: list[ShyftRead]
    narrative_summary: Optional[str] = None


FeedItemRead = Union[ShyftRead, CascadeShyftRead]


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


class ShyftTraceRead(BaseModel):
    shyft: ShyftRead
    rolling_metric: RollingMetricTraceRead
    source_stat: SourceStatContextRead
    baseline_samples: list[BaselineSampleRead]
    discussion_preview: list[CommentRead] = []
    feed_context: Optional[FeedContextRead] = None


class PaginatedShyfts(BaseModel):
    items: list[FeedItemRead]
    has_more: bool
    next_cursor: Optional[int]
    feed_context: Optional[FeedContextRead] = None
