import { useState } from 'react';

import type { Signal } from '../types';
import type { ReactionType } from '../types';
import {
  formatDelta,
  formatEventDate,
  formatRelativeTime,
  formatSignalLabel,
  getImportanceScore,
  getMetricLabel,
  getImportance,
  formatSignalSummary,
  getSignalDirection,
} from '../lib/signalFormat';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import { CommentsPanel } from './CommentsPanel';

const toneMap: Record<Signal['signal_type'], string> = {
  SPIKE: 'border border-emerald-500/20 bg-emerald-500/10 text-emerald-300',
  DROP: 'border border-rose-500/20 bg-rose-500/10 text-rose-300',
  SHIFT: 'border border-amber-500/20 bg-amber-500/10 text-amber-300',
  CONSISTENCY: 'border border-sky-500/20 bg-sky-500/10 text-sky-300',
  OUTLIER: 'border border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-300',
};

const directionTone: Record<'positive' | 'negative' | 'neutral', {
  rowGlow: string;
  rail: string;
  summary: string;
  delta: string;
  meta: string;
  context: string;
}> = {
  positive: {
    rowGlow: 'hover:bg-white/[0.035]',
    rail: 'bg-success',
    summary: 'text-ink',
    delta: 'text-success',
    meta: 'text-muted',
    context: 'text-muted/80',
  },
  negative: {
    rowGlow: 'hover:bg-white/[0.035]',
    rail: 'bg-danger',
    summary: 'text-ink',
    delta: 'text-danger',
    meta: 'text-muted',
    context: 'text-muted/80',
  },
  neutral: {
    rowGlow: 'hover:bg-white/[0.035]',
    rail: 'bg-slate-400',
    summary: 'text-ink',
    delta: 'text-ink',
    meta: 'text-muted',
    context: 'text-muted/80',
  },
};

const importanceBadgeTone: Record<'High' | 'Medium' | 'Watch', string> = {
  High: 'border border-accent/30 bg-accentSoft text-[#ffd8bd]',
  Medium: 'border border-border bg-white/[0.04] text-muted',
  Watch: 'border border-border/70 bg-transparent text-muted/70',
};

const reactionMeta: Array<{ type: ReactionType; label: string }> = [
  { type: 'strong', label: 'Strong' },
  { type: 'agree', label: 'Agree' },
  { type: 'risky', label: 'Risky' },
];

export function SignalCard({ signal, onOpenDetail }: { signal: Signal; onOpenDetail?: (id: number) => void }) {
  const importance = getImportance(signal);
  const importanceScore = getImportanceScore(signal);
  const summary = formatSignalSummary(signal);
  const direction = getSignalDirection(signal);
  const directionStyles = directionTone[direction];
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const reactToSignal = useSignalStore((state) => state.reactToSignal);
  const [showComments, setShowComments] = useState(false);

  async function handleReactionClick(reactionType: ReactionType) {
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    try {
      await reactToSignal(signal.id, reactionType);
    } catch {
      // store handles rollback + error state
    }
  }

  return (
    <article
      className={`group relative grid grid-cols-[minmax(0,1fr),112px] gap-3 border-b border-border bg-transparent px-4 py-4 transition duration-150 sm:grid-cols-[minmax(0,1.75fr),132px] ${directionStyles.rowGlow}`}
    >
      <div className={`absolute inset-y-2.5 left-0 w-[3px] rounded-full ${directionStyles.rail} ${importance === 'Watch' ? 'opacity-35' : 'opacity-75'}`} />
      <div className="min-w-0 pl-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${toneMap[signal.signal_type]}`}>
            {formatSignalLabel(signal.signal_type)}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${importanceBadgeTone[importance]}`}>
            {importance}
          </span>
        </div>
        <div className="mt-1.5 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
          <h3 className="text-[24px] font-semibold text-ink">{signal.player_name}</h3>
          <span className="text-xs uppercase tracking-[0.18em] text-muted">{getMetricLabel(signal)}</span>
        </div>
        <p className={`mt-1 text-[14px] font-medium leading-5 ${directionStyles.summary}`}>{summary}</p>
        <div className={`mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] ${directionStyles.meta}`}>
          <span>{signal.team_name}</span>
          <span className="text-white/10">•</span>
          <span>{signal.league_name}</span>
          {signal.event_date ? (
            <>
              <span className="text-white/10">•</span>
              <span>{formatEventDate(signal.event_date)}</span>
            </>
          ) : null}
          <span className="text-white/10">•</span>
          <span>Z {signal.z_score.toFixed(2)}</span>
          <span className="text-white/10">•</span>
          <span>{formatRelativeTime(signal.created_at)}</span>
          {importance === 'High' ? (
            <>
              <span className="text-white/10">•</span>
              <span>{importanceScore.toFixed(0)}</span>
            </>
          ) : null}
        </div>
        <div className={`mt-1 text-[11px] leading-4 ${directionStyles.context}`}>{signal.explanation}</div>
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {reactionMeta.map(({ type, label }) => {
            const active = signal.user_reaction === type;
            const count = signal.reaction_summary[type];
            return (
              <button
                key={type}
                type="button"
                onClick={() => void handleReactionClick(type)}
                className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.14em] transition ${
                  active
                    ? type === 'strong'
                      ? 'bg-transparent text-success'
                      : type === 'risky'
                        ? 'bg-transparent text-warning'
                        : 'bg-transparent text-[#ffd8bd]'
                    : 'bg-transparent text-muted/70 hover:text-ink'
                }`}
              >
                {label} {count > 0 ? count : ''}
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => setShowComments((v) => !v)}
            className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.14em] transition ${showComments ? 'text-ink' : 'text-muted/70 hover:text-ink'}`}
          >
            {showComments ? 'Hide' : 'Comments'}
          </button>
          {onOpenDetail != null && (
            <button
              type="button"
              onClick={() => onOpenDetail(signal.id)}
              className="ml-auto rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.14em] text-muted/80 transition hover:text-[#ffd8bd]"
            >
              Why →
            </button>
          )}
        </div>
        {showComments && (
          <div className="mt-2 border-t border-border pt-2">
            <CommentsPanel signalId={signal.id} />
          </div>
        )}
      </div>
      <div className="self-center justify-self-end text-right">
        <div className={`text-[25px] font-semibold tracking-tight tabular-nums ${directionStyles.delta}`}>{formatDelta(signal)}</div>
        <div className="mt-0.5 text-[11px]">
          <span className="font-medium text-ink">{signal.current_value.toFixed(1)}</span>
          <span className="mx-1 text-white/10">/</span>
          <span className="text-muted">{signal.baseline_value.toFixed(1)}</span>
        </div>
      </div>
    </article>
  );
}
