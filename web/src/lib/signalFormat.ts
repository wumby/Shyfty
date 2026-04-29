import type { Signal } from '../types';

export function normalizeExpectedCopy(text: string): string {
  return text
    .replace(/\brecent baseline over (?:the )?last \d+ games\b/gi, 'expected')
    .replace(/\bhis recent baseline over (?:the )?last \d+ games\b/gi, 'expected')
    .replace(/\bthe recent baseline\b/gi, 'expected')
    .replace(/\brecent baseline\b/gi, 'expected')
    .replace(/\blast \d+ games\b/gi, 'expected')
    .replace(/\bbaseline\b/gi, 'expected');
}

export function formatMetricName(metricName: string): string {
  return metricName.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

const metricLabels: Record<string, string> = {
  points: 'Points',
  rebounds: 'Rebounds',
  assists: 'Assists',
  steals: 'Steals',
  blocks: 'Blocks',
  turnovers: 'Turnovers',
  minutes_played: 'Minutes',
  usage_rate: 'Usage Rate',
  passing_yards: 'Passing Yards',
  rushing_yards: 'Rushing Yards',
  receiving_yards: 'Receiving Yards',
  touchdowns: 'Touchdowns',
  pace: 'Pace',
  off_rating: 'Offensive Rating',
  fg_pct: 'Field Goal %',
  fg3_pct: '3PT %',
};

export function getMetricLabel(signal: Signal): string {
  return metricLabels[signal.metric_name] || signal.metric_label || formatMetricName(signal.metric_name);
}

export function getImportanceScore(signal: Signal): number {
  if (typeof signal.signal_score === 'number') return signal.signal_score;
  if (typeof signal.importance === 'number') return signal.importance;

  const strength = Math.abs(signal.z_score);
  const typeFloor: Record<Signal['signal_type'], number> = {
    OUTLIER: 8,
    SWING: 6,
    SHIFT: 4,
  };

  return Math.min(typeFloor[signal.signal_type] + Math.min(strength, 4), 10);
}

export function formatSignalLabel(signalType: Signal['signal_type']): string {
  const labels: Record<Signal['signal_type'], string> = {
    SHIFT: 'Shift',
    SWING: 'Swing',
    OUTLIER: 'Outlier',
  };
  return labels[signalType];
}

export function getImportance(signal: Signal): 'High' | 'Medium' | 'Watch' {
  const score = getImportanceScore(signal);
  if (score >= 8) return 'High';
  if (score >= 6) return 'Medium';
  return 'Watch';
}

export function getDeltaPercent(signal: Signal): number | null {
  return typeof signal.movement_pct === 'number' && Number.isFinite(signal.movement_pct)
    ? signal.movement_pct
    : null;
}

export function formatDelta(signal: Signal): string {
  const rawDelta = signal.current_value - signal.baseline_value;
  const formatted = Number.isInteger(rawDelta) ? rawDelta.toFixed(0) : rawDelta.toFixed(1);
  return `${rawDelta >= 0 ? '+' : ''}${formatted}`;
}

export function getSignalDirection(signal: Signal): 'positive' | 'negative' | 'neutral' {
  const rawDelta = signal.current_value - signal.baseline_value;
  if (Math.abs(rawDelta) < 0.05) return 'neutral';
  return rawDelta > 0 ? 'positive' : 'negative';
}

export function formatMovementLabel(signal: Signal): string {
  const metric = getMetricLabel(signal);
  const deltaPercent = getDeltaPercent(signal);
  if (deltaPercent === null) {
    return `${metric} vs baseline`;
  }

  return `${deltaPercent >= 0 ? '+' : ''}${Math.round(deltaPercent)}% vs baseline`;
}

export function formatSignalSummary(signal: Signal): string {
  if (signal.narrative_summary) return signal.narrative_summary;

  const metric = getMetricLabel(signal);
  const rawDelta = signal.current_value - signal.baseline_value;
  const direction = rawDelta >= 0 ? 'above' : 'below';
  return `${metric} is ${Math.abs(rawDelta).toFixed(1)} ${direction} baseline.`;
}

export function formatEventDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatGameContext(signal: Signal): string {
  const parts = [
    signal.event_date ? formatEventDate(signal.event_date) : null,
    signal.opponent ? `vs ${signal.opponent}` : null,
    signal.home_away,
    signal.game_result,
    signal.final_score,
  ].filter(Boolean);

  return parts.join(' · ');
}

export function formatRelativeTime(value: string): string {
  const then = new Date(value).getTime();
  const now = Date.now();
  const diffSeconds = Math.max(0, Math.round((now - then) / 1000));

  if (diffSeconds < 45) return 'just now';
  if (diffSeconds < 3600) return `${Math.round(diffSeconds / 60)}m ago`;
  if (diffSeconds < 86400) return `${Math.round(diffSeconds / 3600)}h ago`;
  if (diffSeconds < 604800) return `${Math.round(diffSeconds / 86400)}d ago`;
  return new Date(value).toLocaleDateString();
}

export function getSignalMomentum(signal: Signal, tracked = false, sortMode?: string | null): number {
  const totalReactions = signal.reaction_summary.strong + signal.reaction_summary.agree + signal.reaction_summary.risky;
  const hoursSincePost = Math.max(0, (Date.now() - new Date(signal.created_at).getTime()) / 3600000);
  const recencyBoost = Math.max(0, 2.2 - hoursSincePost / 10);
  const engagementBoost = Math.min(3, totalReactions * 0.25 + signal.comment_count * 0.55);
  const followBoost = tracked ? 2.4 : 0;
  const sortBoost = sortMode === 'most_discussed' ? engagementBoost * 0.6 : 0;
  const importanceBoost = getImportanceScore(signal) / 5.5;

  return importanceBoost + engagementBoost + recencyBoost + followBoost + sortBoost;
}
