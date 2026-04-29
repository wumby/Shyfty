export type SignalSeverity = 'SHIFT' | 'SWING' | 'OUTLIER';
export type SignalType = SignalSeverity;
export type ReactionType = 'strong' | 'agree' | 'risky';
export type SortMode = 'newest' | 'most_important' | 'biggest_deviation' | 'most_discussed';
export type FeedMode = 'all' | 'following' | 'for_you';

export interface ReactionSummary {
  strong: number;
  agree: number;
  risky: number;
}

export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface FreshnessContext {
  state: 'fresh' | 'delayed' | 'stale' | 'refreshing' | 'unknown';
  label: string;
  coverage_summary: string;
  delayed_data_message: string | null;
  ingest_age_minutes: number | null;
  event_age_hours: number | null;
}

export interface SignalDebugTrace {
  baseline: number;
  actual: number;
  delta: number;
  z_score: number;
  sample_size: number;
  thresholds: Record<string, number | null>;
  conditions: Record<string, boolean>;
  passed: boolean;
}

export interface Signal {
  id: number;
  subject_type?: 'player' | 'team';
  player_id: number | null;
  team_id: number;
  game_id: number;
  player_name: string;
  team_name: string;
  league_name: string;
  signal_type: SignalType;
  severity: SignalSeverity;
  metric_name: string;
  current_value: number;
  baseline_value: number;
  performance: number | null;
  deviation: number | null;
  z_score: number;
  signal_score: number;
  score_explanation?: string | null;
  explanation: string;
  importance?: number;
  baseline_window?: string;
  event_date?: string;
  movement_pct: number | null;
  metric_label?: string;
  trend_direction?: 'up' | 'down' | 'flat';
  opponent?: string | null;
  home_away?: string | null;
  game_result?: string | null;
  final_score?: string | null;
  summary_template?: string;
  summary_template_inputs?: {
    current_value: number;
    baseline_value: number;
    movement_pct: number | null;
    baseline_window: string;
    trend_direction: 'up' | 'down' | 'flat';
  };
  classification_reason?: string;
  debug_trace?: SignalDebugTrace;
  narrative_summary?: string;
  streak: number;
  reaction_summary: ReactionSummary;
  user_reaction: ReactionType | null;
  comment_count: number;
  is_favorited: boolean;
  created_at: string;
  freshness: FreshnessContext | null;
}

export interface Player {
  id: number;
  name: string;
  position: string;
  team_name: string;
  league_name: string;
  signal_count?: number;
  is_followed: boolean;
}

export interface PlayerDetail extends Player {
  signal_count: number;
}

export interface Team {
  id: number;
  name: string;
  league_name: string;
  player_count: number;
  signal_count?: number;
  is_followed: boolean;
}

export interface MetricSeriesPoint {
  game_date: string;
  metrics: Record<string, number>;
}

export interface TeamDetail extends Team {
  players: Player[];
  recent_signals: Signal[];
}

export interface FeedContext {
  feed_mode: FeedMode;
  sort_mode: SortMode;
  personalization_reason: string | null;
}

export interface PaginatedSignals {
  items: Signal[];
  has_more: boolean;
  next_cursor: number | null;
  feed_context: FeedContext | null;
}

export interface BaselineSample {
  stat_id: number;
  game_id: number;
  game_date: string;
  value: number;
}

export interface SignalTrace {
  signal: Signal;
  rolling_metric: {
    metric_name: string;
    rolling_avg: number;
    rolling_stddev: number;
    z_score: number;
  } | null;
  source_stat: {
    game_date: string;
    current_value: number;
    raw_stats: Record<string, number>;
  } | null;
  baseline_samples: BaselineSample[];
  discussion_preview: Comment[];
  related_signals: Signal[];
  feed_context: FeedContext | null;
}

export interface Comment {
  id: number;
  signal_id: number;
  user_id: number;
  user_email: string;
  body: string;
  created_at: string;
  updated_at: string;
  is_edited: boolean;
  can_edit: boolean;
  can_delete: boolean;
  can_report: boolean;
}

export interface GameLogRow {
  game_id: number;
  game_date: string;
  season: string | null;
  opponent: string;
  home_away: 'Home' | 'Away';
  points: number | null;
  rebounds: number | null;
  assists: number | null;
  passing_yards: number | null;
  rushing_yards: number | null;
  receiving_yards: number | null;
  touchdowns: number | null;
  usage_rate: number | null;
}

export interface SeasonAveragesRow {
  season: string;
  games_played: number;
  points: number | null;
  rebounds: number | null;
  assists: number | null;
  passing_yards: number | null;
  rushing_yards: number | null;
  receiving_yards: number | null;
  touchdowns: number | null;
  usage_rate: number | null;
}

export interface SignalFilters {
  league?: string;
  signal_type?: string;
  player?: string;
  sort?: SortMode;
  feed?: FeedMode;
  date_from?: string;
  date_to?: string;
}

export interface IngestRun {
  started_at: string;
  finished_at: string | null;
  status: string;
  duration_seconds: number | null;
  error_message: string | null;
}

export interface IngestStatus {
  status: 'idle' | 'running' | 'error';
  last_updated: string | null;
  started_at: string | null;
  finished_at: string | null;
  current_run_duration_seconds: number | null;
  last_error: string | null;
  recent_runs: IngestRun[];
}

export interface SavedView {
  id: number;
  name: string;
  league: string | null;
  signal_type: string | null;
  player: string | null;
  sort_mode: SortMode;
  feed_mode: FeedMode;
  created_at: string;
  updated_at: string;
}

export interface ProfilePreferences {
  preferred_league: string | null;
  preferred_signal_type: string | null;
  default_sort_mode: SortMode;
  default_feed_mode: FeedMode;
  notification_releases: boolean;
  notification_digest: boolean;
}

export interface UserProfile {
  preferences: ProfilePreferences;
  follows: {
    players: number[];
    teams: number[];
  };
  saved_views: SavedView[];
}
