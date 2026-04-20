import type { Signal } from '../types';

export function formatMetricName(metricName: string): string {
  return metricName.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
}

export function getMetricLabel(signal: Signal): string {
  return signal.metric_label || formatMetricName(signal.metric_name);
}

export function getImportanceScore(signal: Signal): number {
  if (typeof signal.importance === 'number') return signal.importance;

  const strength = Math.abs(signal.z_score);
  const typeFloor: Record<Signal['signal_type'], number> = {
    OUTLIER: 85,
    SPIKE: 72,
    DROP: 72,
    SHIFT: 60,
    CONSISTENCY: 52,
  };

  return Math.min(typeFloor[signal.signal_type] + Math.min(strength * 8, 15), 100);
}

export function formatSignalLabel(signalType: Signal['signal_type']): string {
  const labels: Record<Signal['signal_type'], string> = {
    SPIKE: 'Spike',
    DROP: 'Drop',
    SHIFT: 'Shift',
    CONSISTENCY: 'Consistency',
    OUTLIER: 'Outlier',
  };
  return labels[signalType];
}

export function getImportance(signal: Signal): 'High' | 'Medium' | 'Watch' {
  const score = getImportanceScore(signal);
  if (score >= 85) return 'High';
  if (score >= 65) return 'Medium';
  return 'Watch';
}

export function getDeltaPercent(signal: Signal): number | null {
  if (signal.movement_pct !== null && signal.movement_pct !== undefined) return signal.movement_pct;
  if (Math.abs(signal.baseline_value) < 0.05) return null;
  return ((signal.current_value - signal.baseline_value) / signal.baseline_value) * 100;
}

export function formatDelta(signal: Signal): string {
  const deltaPercent = getDeltaPercent(signal);
  if (deltaPercent === null) {
    const rawDelta = signal.current_value - signal.baseline_value;
    return `${rawDelta >= 0 ? '+' : ''}${rawDelta.toFixed(1)}`;
  }
  const rounded = Math.round(deltaPercent);
  return `${rounded >= 0 ? '+' : ''}${rounded}%`;
}

export function getSignalDirection(signal: Signal): 'positive' | 'negative' | 'neutral' {
  const deltaPercent = getDeltaPercent(signal);

  if (signal.signal_type === 'CONSISTENCY') return 'neutral';
  if (deltaPercent === null) {
    const rawDelta = signal.current_value - signal.baseline_value;
    if (Math.abs(rawDelta) < 0.05) return 'neutral';
    return rawDelta > 0 ? 'positive' : 'negative';
  }

  if (Math.abs(deltaPercent) < 1) return 'neutral';
  return deltaPercent > 0 ? 'positive' : 'negative';
}

export function formatMovementLabel(signal: Signal): string {
  const metric = getMetricLabel(signal);
  const deltaPercent = getDeltaPercent(signal);
  if (deltaPercent === null) {
    return `${metric} vs baseline`;
  }

  const direction = deltaPercent >= 0 ? 'above' : 'below';
  return `${Math.abs(Math.round(deltaPercent))}% ${direction} baseline`;
}

export function formatSignalSummary(signal: Signal): string {
  if (signal.narrative_summary) return signal.narrative_summary;

  const metric = getMetricLabel(signal);
  const deltaPercent = getDeltaPercent(signal);
  const window = signal.baseline_window ?? 'recent baseline';

  if (deltaPercent === null) {
    const rawDelta = signal.current_value - signal.baseline_value;
    return `${metric} moved ${rawDelta >= 0 ? 'above' : 'below'} ${window}.`;
  }

  const rounded = Math.abs(Math.round(deltaPercent));
  const direction = deltaPercent >= 0 ? 'above' : 'below';
  return `${metric} is ${rounded}% ${direction} ${window}.`;
}

export function formatEventDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
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
  const importanceBoost = getImportanceScore(signal) / 55;

  return importanceBoost + engagementBoost + recencyBoost + followBoost + sortBoost;
}
