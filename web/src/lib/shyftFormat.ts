import type { Shyft } from '../types';

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

export function getMetricLabel(signal: Shyft): string {
  return metricLabels[signal.metric_name] || signal.metric_label || formatMetricName(signal.metric_name);
}

export function getImportanceScore(signal: Shyft): number {
  if (typeof signal.shyft_score === 'number') return signal.shyft_score;
  if (typeof signal.importance === 'number') return signal.importance;

  const strength = Math.abs(signal.z_score);
  const typeFloor: Record<Shyft['shyft_type'], number> = {
    OUTLIER: 8,
    SWING: 6,
    SHIFT: 4,
  };

  return Math.min(typeFloor[signal.shyft_type] + Math.min(strength, 4), 10);
}

export function formatShyftLabel(shyftType: Shyft['shyft_type']): string {
  const labels: Record<Shyft['shyft_type'], string> = {
    SHIFT: 'Shift',
    SWING: 'Swing',
    OUTLIER: 'Outlier',
  };
  return labels[shyftType];
}

export function getImportance(signal: Shyft): 'High' | 'Medium' | 'Watch' {
  const score = getImportanceScore(signal);
  if (score >= 8) return 'High';
  if (score >= 6) return 'Medium';
  return 'Watch';
}

export function getDeltaPercent(signal: Shyft): number | null {
  return typeof signal.movement_pct === 'number' && Number.isFinite(signal.movement_pct)
    ? signal.movement_pct
    : null;
}

export function formatDelta(signal: Shyft): string {
  const rawDelta = signal.current_value - signal.baseline_value;
  const formatted = Number.isInteger(rawDelta) ? rawDelta.toFixed(0) : rawDelta.toFixed(1);
  return `${rawDelta >= 0 ? '+' : ''}${formatted}`;
}

export function getShyftDirection(signal: Shyft): 'positive' | 'negative' | 'neutral' {
  const rawDelta = signal.current_value - signal.baseline_value;
  if (Math.abs(rawDelta) < 0.05) return 'neutral';
  return rawDelta > 0 ? 'positive' : 'negative';
}

export function formatMovementLabel(signal: Shyft): string {
  const metric = getMetricLabel(signal);
  const deltaPercent = getDeltaPercent(signal);
  if (deltaPercent === null) {
    return `${metric} vs baseline`;
  }

  return `${deltaPercent >= 0 ? '+' : ''}${Math.round(deltaPercent)}% vs baseline`;
}

export function formatSignalSummary(signal: Shyft): string {
  if (signal.narrative_summary) return signal.narrative_summary;

  const metric = getMetricLabel(signal);
  const rawDelta = signal.current_value - signal.baseline_value;
  const direction = rawDelta >= 0 ? 'above' : 'below';
  return `${metric} is ${Math.abs(rawDelta).toFixed(1)} ${direction} baseline.`;
}

export function formatEventDate(value: string): string {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' })
      .format(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))));
  }
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export function formatGameContext(signal: Shyft): string {
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

export function getSignalMomentum(signal: Shyft, tracked = false, sortMode?: string | null): number {
  const totalReactions = signal.reaction_summary.shyft_up + signal.reaction_summary.shyft_down + signal.reaction_summary.shyft_eye;
  const hoursSincePost = Math.max(0, (Date.now() - new Date(signal.created_at).getTime()) / 3600000);
  const recencyBoost = Math.max(0, 2.2 - hoursSincePost / 10);
  const engagementBoost = Math.min(3, totalReactions * 0.25 + signal.comment_count * 0.55);
  const followBoost = tracked ? 2.4 : 0;
  const sortBoost = sortMode === 'most_discussed' ? engagementBoost * 0.6 : 0;
  const importanceBoost = getImportanceScore(signal) / 5.5;

  return importanceBoost + engagementBoost + recencyBoost + followBoost + sortBoost;
}
