export type ShyftSeverity = 'SHIFT' | 'SWING' | 'OUTLIER';
export type ShyftType = ShyftSeverity;
export type ShyftReaction = 'SHYFT_UP' | 'SHYFT_DOWN' | 'SHYFT_EYE';
export type ReactionType = ShyftReaction;
export type SortMode = 'newest' | 'most_important' | 'biggest_deviation' | 'most_discussed';
export type FeedMode = 'all' | 'following' | 'for_you';

export const SHYFT_REACTION_ORDER: ShyftReaction[] = ['SHYFT_UP', 'SHYFT_DOWN', 'SHYFT_EYE'];

export interface ReactionSummary {
  shyft_up: number;
  shyft_down: number;
  shyft_eye: number;
}

export interface ReactionEntry {
  type: ShyftReaction;
  count: number;
  reactedByCurrentUser: boolean;
}

export interface User {
  id: number;
  email: string;
  display_name?: string | null;
  created_at: string;
}

export interface ShyftDebugTrace {
  baseline: number;
  actual: number;
  delta: number;
  z_score: number;
  sample_size: number;
  thresholds: Record<string, number | null>;
  conditions: Record<string, boolean>;
  passed: boolean;
}

export interface Shyft {
  type?: 'shyft';
  id: number;
  subject_type?: 'player' | 'team';
  player_id: number | null;
  team_id: number;
  game_id: number;
  player_name: string;
  team_name: string;
  league_name: string;
  shyft_type: ShyftType;
  severity: ShyftSeverity;
  metric_name: string;
  current_value: number;
  baseline_value: number;
  performance: number | null;
  deviation: number | null;
  z_score: number;
  shyft_score: number;
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
  debug_trace?: ShyftDebugTrace;
  narrative_summary?: string;
  streak: number;
  reaction_summary: ReactionSummary;
  user_reaction: ShyftReaction | null;
  reactions?: ReactionEntry[];
  user_reactions?: ShyftReaction[];
  comment_count: number;
  created_at: string;
}

export interface CascadePlayer {
  id: number | null;
  name: string;
}

export interface CascadeTrigger {
  player: CascadePlayer;
  shyft_id: number;
  stat: string;
  metric_label: string;
  delta: number;
  delta_percent: number | null;
  shyft_type: ShyftType;
  shyft_score: number;
}

export interface CascadeContributor extends CascadeTrigger {}

export interface CascadeShyft {
  type: 'cascade';
  id: string;
  game_id: number;
  team_id: number;
  team: string;
  league_name: string;
  game_date: string;
  created_at: string;
  trigger: CascadeTrigger;
  contributors: CascadeContributor[];
  underlying_shyfts: Shyft[];
  narrative_summary: string | null;
}

export type FeedItem = Shyft | CascadeShyft;

export interface Player {
  id: number;
  name: string;
  position: string;
  team_name: string;
  league_name: string;
  shyft_count?: number;
  is_followed: boolean;
}

export interface PlayerDetail extends Player {
  shyft_count: number;
  recent_box_scores: PlayerBoxScore[];
}

export interface Team {
  id: number;
  name: string;
  league_name: string;
  player_count: number;
  shyft_count?: number;
  is_followed: boolean;
}

export interface MetricSeriesPoint {
  game_date: string;
  metrics: Record<string, number>;
}

export interface TeamDetail extends Team {
  players: Player[];
  recent_shyfts: Shyft[];
  recent_box_scores: TeamBoxScore[];
}

export interface PlayerBoxScore {
  game_id: number;
  game_date: string;
  season?: string | null;
  opponent: string;
  home_away: string;
  team_score?: number | null;
  opponent_score?: number | null;
  result?: 'W' | 'L' | 'T' | null;
  points?: number | null;
  rebounds?: number | null;
  assists?: number | null;
  passing_yards?: number | null;
  passing_completions?: number | null;
  passing_attempts?: number | null;
  interceptions?: number | null;
  rushing_yards?: number | null;
  rushing_attempts?: number | null;
  receiving_yards?: number | null;
  receptions?: number | null;
  targets?: number | null;
  touchdowns?: number | null;
  sacks?: number | null;
  fumbles_lost?: number | null;
  usage_rate?: number | null;
  steals?: number | null;
  blocks?: number | null;
  turnovers?: number | null;
  minutes_played?: number | null;
  plus_minus?: number | null;
  fg_pct?: number | null;
  fg3_pct?: number | null;
  ft_pct?: number | null;
}

export interface TeamBoxScore {
  game_id: number;
  game_date: string;
  season?: string | null;
  opponent: string;
  home_away: string;
  points?: number | null;
  rebounds?: number | null;
  assists?: number | null;
  fg_pct?: number | null;
  fg3_pct?: number | null;
  turnovers?: number | null;
  pace?: number | null;
  off_rating?: number | null;
  total_yards?: number | null;
  first_downs?: number | null;
  penalties?: number | null;
  penalty_yards?: number | null;
  turnovers_forced?: number | null;
  turnovers_lost?: number | null;
  third_down_pct?: number | null;
  redzone_pct?: number | null;
  team_score?: number | null;
  opponent_score?: number | null;
  result?: 'W' | 'L' | 'T' | null;
}

export interface FeedContext {
  feed_mode: FeedMode;
  sort_mode: SortMode;
  personalization_reason: string | null;
}

export interface PaginatedShyfts {
  items: FeedItem[];
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

export interface ShyftTrace {
  shyft: Shyft;
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
  feed_context: FeedContext | null;
}

export interface Comment {
  id: number;
  shyft_id: number;
  user_id: number;
  user_email: string;
  user_display_name?: string;
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
  passing_completions: number | null;
  passing_attempts: number | null;
  interceptions: number | null;
  rushing_yards: number | null;
  rushing_attempts: number | null;
  receiving_yards: number | null;
  receptions: number | null;
  targets: number | null;
  touchdowns: number | null;
  sacks: number | null;
  fumbles_lost: number | null;
  usage_rate: number | null;
}

export interface SeasonAveragesRow {
  season: string;
  games_played: number;
  points: number | null;
  rebounds: number | null;
  assists: number | null;
  passing_yards: number | null;
  passing_completions: number | null;
  passing_attempts: number | null;
  interceptions: number | null;
  rushing_yards: number | null;
  rushing_attempts: number | null;
  receiving_yards: number | null;
  receptions: number | null;
  targets: number | null;
  touchdowns: number | null;
  sacks: number | null;
  fumbles_lost: number | null;
  usage_rate: number | null;
}

export interface ShyftFilters {
  league?: string;
  shyft_type?: string;
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

export interface ProfilePreferences {
  preferred_league: string | null;
  preferred_shyft_type: string | null;
  default_sort_mode: SortMode;
  default_feed_mode: FeedMode;
  notification_releases: boolean;
  notification_digest: boolean;
}

export interface UserProfile {
  display_name?: string | null;
  preferences: ProfilePreferences;
  follows: {
    players: number[];
    teams: number[];
  };
}
