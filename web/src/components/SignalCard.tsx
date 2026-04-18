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
  const toggleFavorite = useSignalStore((state) => state.toggleFavorite);
  const [showComments, setShowComments] = useState(false);

  async function handleReactionClick(reactionType: ReactionType) {
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    try {
      await reactToSignal(signal.id, reactionType);
    } catch {
      // store handles rollback
    }
  }

  async function handleFavoriteClick() {
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    await toggleFavorite(signal.id);
  }

  return (
    <article
      className={`group relative grid grid-cols-[minmax(0,1fr),104px] gap-3 border-b border-border bg-transparent px-4 py-4 transition duration-150 sm:grid-cols-[minmax(0,1fr),118px] sm:px-5 ${directionStyles.rowGlow}`}
    >
      <div className={`absolute inset-y-4 left-0 w-[3px] rounded-full ${directionStyles.rail} ${importance === 'Watch' ? 'opacity-35' : 'opacity-75'}`} />
      <div className="min-w-0 pl-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${toneMap[signal.signal_type]}`}>
            {formatSignalLabel(signal.signal_type)}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${importanceBadgeTone[importance]}`}>
            {importance}
          </span>
        </div>
        <div className="mt-2 flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
          <h3 className="text-[22px] font-semibold leading-none text-ink sm:text-[24px]">{signal.player_name}</h3>
          <span className="text-[11px] uppercase tracking-[0.18em] text-muted">{getMetricLabel(signal)}</span>
        </div>
        <p className={`mt-2 max-w-3xl text-[14px] font-medium leading-5 ${directionStyles.summary}`}>{summary}</p>
        <div className={`mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] ${directionStyles.meta}`}>
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
          <span>{formatRelativeTime(signal.created_at)}</span>
          {signal.comment_count > 0 ? (
            <>
              <span className="text-white/10">•</span>
              <span>{signal.comment_count} discussing</span>
            </>
          ) : null}
        </div>
        {signal.freshness && signal.freshness.state !== 'fresh' ? (
          <div className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
            signal.freshness.state === 'stale'
              ? 'border-danger/30 bg-danger/10 text-danger'
              : 'border-warning/30 bg-warning/10 text-warning'
          }`}>
            {signal.freshness.state === 'stale' ? 'Stale board context' : 'Delayed data'}
          </div>
        ) : null}
        <div className={`mt-2 text-[12px] leading-5 ${directionStyles.context}`}>
          {signal.explanation}
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {reactionMeta.map(({ type, label }) => {
            const active = signal.user_reaction === type;
            const count = signal.reaction_summary[type];
            return (
              <button
                key={type}
                type="button"
                onClick={() => void handleReactionClick(type)}
                className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] transition ${
                  active
                    ? type === 'strong'
                      ? 'border-success/30 bg-success/10 text-success'
                      : type === 'risky'
                        ? 'border-warning/30 bg-warning/10 text-warning'
                        : 'border-accent/30 bg-accentSoft text-[#ffd8bd]'
                    : 'border-transparent bg-transparent text-muted/70 hover:border-border hover:text-ink'
                }`}
              >
                {label} {count > 0 ? count : ''}
              </button>
            );
          })}

          {/* Favorite star */}
          <button
            type="button"
            onClick={() => void handleFavoriteClick()}
            title={signal.is_favorited ? 'Remove from saved' : 'Save signal'}
            className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] transition ${
              signal.is_favorited
                ? 'border-amber-500/30 bg-amber-500/10 text-amber-300'
                : 'border-transparent text-muted/70 hover:border-border hover:text-ink'
            }`}
          >
            {signal.is_favorited ? '★' : '☆'}
          </button>

          <button
            type="button"
            onClick={() => setShowComments((v) => !v)}
            className={`rounded-full border px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] transition ${
              showComments
                ? 'border-border bg-white/[0.04] text-ink'
                : 'border-transparent text-muted/70 hover:border-border hover:text-ink'
            }`}
          >
            {showComments ? 'Hide' : `Comments${signal.comment_count > 0 ? ` ${signal.comment_count}` : ''}`}
          </button>
          {onOpenDetail != null && (
            <button
              type="button"
              onClick={() => onOpenDetail(signal.id)}
              className="ml-auto rounded-full border border-transparent px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] text-muted/80 transition hover:border-border hover:text-[#ffd8bd]"
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
      <div className="self-start justify-self-end pt-1 text-right">
        <div className={`text-[24px] font-semibold tracking-tight tabular-nums sm:text-[26px] ${directionStyles.delta}`}>{formatDelta(signal)}</div>
        <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-muted">
          <span className="text-ink">{signal.current_value.toFixed(1)}</span>
          <span className="mx-1 text-white/10">/</span>
          <span>{signal.baseline_value.toFixed(1)}</span>
        </div>
        <div className="mt-3 hidden rounded-[18px] border border-border bg-white/[0.03] px-2.5 py-2 text-[10px] uppercase tracking-[0.16em] text-muted sm:block">
          Z {signal.z_score.toFixed(2)}
          {importance === 'High' ? <span className="ml-2 text-[#ffd8bd]">{importanceScore.toFixed(0)}</span> : null}
        </div>
      </div>
    </article>
  );
}
