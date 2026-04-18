export type SignalType = 'SPIKE' | 'DROP' | 'SHIFT' | 'CONSISTENCY' | 'OUTLIER';
export type ReactionType = 'strong' | 'agree' | 'risky';

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

export interface Signal {
  id: number;
  player_id: number;
  player_name: string;
  team_name: string;
  league_name: string;
  signal_type: SignalType;
  metric_name: string;
  current_value: number;
  baseline_value: number;
  z_score: number;
  explanation: string;
  importance?: number;
  baseline_window?: string;
  event_date?: string;
  movement_pct: number | null;
  metric_label?: string;
  trend_direction?: 'up' | 'down' | 'flat';
  summary_template?: string;
  summary_template_inputs?: {
    current_value: number;
    baseline_value: number;
    movement_pct: number | null;
    baseline_window: string;
    trend_direction: 'up' | 'down' | 'flat';
  };
  classification_reason?: string;
  reaction_summary: ReactionSummary;
  user_reaction: ReactionType | null;
  created_at: string;
}

export interface Player {
  id: number;
  name: string;
  position: string;
  team_name: string;
  league_name: string;
}

export interface PlayerDetail extends Player {
  signal_count: number;
}

export interface Team {
  id: number;
  name: string;
  league_name: string;
  player_count: number;
}

export interface MetricSeriesPoint {
  game_date: string;
  metrics: Record<string, number>;
}

export interface TeamDetail extends Team {
  players: Player[];
  recent_signals: Signal[];
}

export interface PaginatedSignals {
  items: Signal[];
  has_more: boolean;
  next_cursor: number | null;
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
}

export interface Comment {
  id: number;
  signal_id: number;
  user_id: number;
  user_email: string;
  body: string;
  created_at: string;
}

export interface SignalFilters {
  league?: string;
  signal_type?: string;
}
