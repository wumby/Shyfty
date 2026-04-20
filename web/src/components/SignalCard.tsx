import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

import type { Signal } from '../types';
import type { ReactionType } from '../types';
import {
  formatDelta,
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
    rowGlow: 'hover:bg-white/[0.045]',
    rail: 'bg-success',
    summary: 'text-ink',
    delta: 'text-success',
    meta: 'text-muted',
    context: 'text-muted/80',
  },
  negative: {
    rowGlow: 'hover:bg-white/[0.045]',
    rail: 'bg-danger',
    summary: 'text-ink',
    delta: 'text-danger',
    meta: 'text-muted',
    context: 'text-muted/80',
  },
  neutral: {
    rowGlow: 'hover:bg-white/[0.045]',
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
  const location = useLocation();

  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const reactToSignal = useSignalStore((state) => state.reactToSignal);
  const toggleFavorite = useSignalStore((state) => state.toggleFavorite);
  const toggleFollowPlayer = useSignalStore((state) => state.toggleFollowPlayer);
  const profile = useSignalStore((state) => state.profile);

  const isPlayerFollowed = profile?.follows.players.includes(signal.player_id) ?? false;
  const isTeamFollowed = profile?.follows.teams.includes(signal.team_id) ?? false;
  const isTracked = isPlayerFollowed || isTeamFollowed;
  const totalReactions = signal.reaction_summary.strong + signal.reaction_summary.agree + signal.reaction_summary.risky;
  const engagementScore = totalReactions + signal.comment_count * 2;
  const engagementLabel =
    totalReactions > 0 || signal.comment_count > 0
      ? `${totalReactions} reaction${totalReactions === 1 ? '' : 's'} • ${signal.comment_count} discussing`
      : 'Be the first read';
  const engagementTone =
    engagementScore >= 12
      ? 'text-[#ffd8bd]'
      : engagementScore >= 4
        ? 'text-ink/85'
        : 'text-muted/85';

  const [expanded, setExpanded] = useState(false);
  const [showComments, setShowComments] = useState(false);
  const compact = onOpenDetail != null;

  async function handleReactionClick(reactionType: ReactionType) {
    if (!currentUser) { openAuth('signin'); return; }
    try { await reactToSignal(signal.id, reactionType); } catch { /* store handles rollback */ }
  }

  async function handleFavoriteClick() {
    if (!currentUser) { openAuth('signin'); return; }
    await toggleFavorite(signal.id);
  }

  async function handleFollowClick() {
    if (!currentUser) { openAuth('signin'); return; }
    await toggleFollowPlayer(signal.player_id, isPlayerFollowed);
  }

  const stop = (e: React.MouseEvent) => e.stopPropagation();

  return (
    <article
      onClick={() => setExpanded((v) => !v)}
      className={`signal-card-enter group relative grid cursor-pointer grid-cols-[minmax(0,1fr),88px] gap-3 border-b border-border px-3 py-2.5 transition-all duration-150 sm:grid-cols-[minmax(0,1fr),96px] sm:px-4 ${directionStyles.rowGlow} ${importance === 'High' ? 'bg-accent/[0.018]' : 'bg-transparent'} ${expanded ? '!bg-white/[0.03]' : ''} ${isTracked ? 'shadow-[inset_0_0_0_1px_rgba(249,115,22,0.08)]' : ''} hover:-translate-y-px`}
    >
      <div className={`absolute inset-y-3 left-0 w-[3px] rounded-full ${directionStyles.rail} ${importance === 'Watch' ? 'opacity-30' : 'opacity-70'}`} />
      {isTracked ? <div className="absolute right-4 top-4 h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_18px_rgba(249,115,22,0.75)]" /> : null}

      <div className="min-w-0 pl-3">
        {/* Level 1: badges */}
        <div className="flex flex-wrap items-center gap-1.5">
          <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${toneMap[signal.signal_type]}`}>
            {formatSignalLabel(signal.signal_type)}
          </span>
          {importance !== 'Watch' && (
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${importanceBadgeTone[importance]}`}>
              {importance}
            </span>
          )}
        </div>

        {/* Level 2: player name (linked) + metric + follow button */}
        <div className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5" onClick={stop}>
          <Link
            to={`/players/${signal.player_id}`}
            state={{ returnTo: `${location.pathname}${location.search}`, fromFeed: true }}
            className="text-[18px] font-semibold leading-none text-ink transition hover:scale-[1.01] hover:text-[#ffd8bd] sm:text-[20px]"
          >
            {signal.player_name}
          </Link>
          <span className="text-[10px] uppercase tracking-[0.18em] text-muted">{getMetricLabel(signal)}</span>
          {currentUser && (
            <button
              type="button"
              onClick={() => void handleFollowClick()}
              className={`ml-1 rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] transition ${
                isPlayerFollowed
                  ? 'border-accent/30 bg-accentSoft text-accent'
                  : 'border-border/60 text-muted/50 hover:border-border hover:text-muted'
              }`}
            >
              {isPlayerFollowed ? '✓ Following' : '+ Follow'}
            </button>
          )}
        </div>

        {/* Level 2: one-line insight */}
        <p className={`mt-1 text-[14px] font-semibold leading-5 ${directionStyles.summary} ${expanded ? '' : 'line-clamp-2'}`}>
          {summary}
        </p>

        {!compact && signal.explanation ? (
          <p className={`mt-1 text-[11px] leading-5 ${directionStyles.context} ${expanded ? '' : 'line-clamp-1'}`}>
            {signal.explanation}
          </p>
        ) : null}

        {/* Level 3: meta strip — always visible */}
        <div className={`mt-1 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] ${directionStyles.meta}`}>
          <span>{signal.team_name}</span>
          <span className="text-white/10">•</span>
          <span>{signal.league_name}</span>
          <span className="text-white/10">•</span>
          <span>{formatRelativeTime(signal.created_at)}</span>
          <span className="text-white/10">•</span>
          <span className={`font-medium ${engagementTone}`}>{engagementLabel}</span>
          {isTracked ? (
            <>
              <span className="text-white/10">•</span>
              <span className="text-accent/85">{isPlayerFollowed ? 'Tracked player' : 'Tracked team'}</span>
            </>
          ) : null}
        </div>

        {/* Expandable detail */}
        <div className={`card-expand ${expanded ? 'open' : ''}`}>
          <div>
            {signal.freshness && signal.freshness.state !== 'fresh' && (
              <div className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                signal.freshness.state === 'stale'
                  ? 'border-danger/30 bg-danger/10 text-danger'
                  : 'border-warning/30 bg-warning/10 text-warning'
              }`}>
                {signal.freshness.state === 'stale' ? 'Stale board context' : 'Delayed data'}
              </div>
            )}
            <div className="mt-2.5 flex flex-wrap items-center gap-1.5" onClick={stop}>
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
                    {label}{count > 0 ? ` ${count}` : ''}
                  </button>
                );
              })}

              <button
                type="button"
                onClick={(e) => { stop(e); void handleFavoriteClick(); }}
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
                onClick={(e) => { stop(e); setShowComments((v) => !v); }}
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
                  onClick={(e) => { stop(e); onOpenDetail(signal.id); }}
                  className="ml-auto rounded-full border border-transparent px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] text-muted/80 transition hover:border-border hover:text-[#ffd8bd]"
                >
                  Why →
                </button>
              )}
            </div>

            {showComments && (
              <div className="mt-2 border-t border-border pt-2" onClick={stop}>
                <CommentsPanel signalId={signal.id} />
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Right: key metric */}
      <div className="self-start justify-self-end pt-0.5 text-right">
        <div className={`text-[18px] font-semibold tracking-tight tabular-nums sm:text-[20px] ${directionStyles.delta}`}>
          {formatDelta(signal)}
        </div>
        <div className="mt-0.5 text-[10px] uppercase tracking-[0.14em] text-muted">
          <span className="text-ink">{signal.current_value.toFixed(1)}</span>
          <span className="mx-1 text-white/10">/</span>
          <span>{signal.baseline_value.toFixed(1)}</span>
        </div>
        {expanded && (
          <div className="mt-2 hidden rounded-[14px] border border-border bg-white/[0.03] px-2 py-1.5 text-[10px] uppercase tracking-[0.16em] text-muted sm:block">
            Z {signal.z_score.toFixed(2)}
            {importance === 'High' ? <span className="ml-1.5 text-[#ffd8bd]">{importanceScore.toFixed(0)}</span> : null}
          </div>
        )}
      </div>
    </article>
  );
}
