import { Link } from 'react-router-dom';

import type { Signal } from '../types';
import { formatDelta, formatEventDate, getMetricLabel, getSignalDirection } from '../lib/signalFormat';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';

interface LastGameSignalCardProps {
  signals: Signal[];
  onOpenDetail?: (signalId: number) => void;
}

function getSignalPriority(signal: Signal): number {
  if (typeof signal.signal_score === 'number') return signal.signal_score;
  if (typeof signal.importance === 'number') return signal.importance;
  return Math.abs(signal.z_score);
}

function getSignalSeverity(signal: Signal): Signal['severity'] {
  return signal.severity ?? signal.signal_type;
}

function getSeverityTone(severity: Signal['severity']): string {
  if (severity === 'OUTLIER') {
    return 'border-fuchsia-300/35 bg-fuchsia-400/15 text-fuchsia-100';
  }
  if (severity === 'SWING') {
    return 'border-amber-300/30 bg-amber-400/10 text-amber-100';
  }
  return 'border-white/10 bg-white/[0.04] text-muted';
}

function formatStatValue(signal: Signal, value: number): string {
  if (signal.metric_name === 'usage_rate') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    const rounded = Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1);
    return `${rounded}%`;
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function formatSignedValue(value: number): string {
  const formatted = Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);
  return `${value >= 0 ? '+' : ''}${formatted}`;
}

function formatScore(signal: Signal): string {
  const score = typeof signal.signal_score === 'number' ? signal.signal_score : signal.importance;
  return typeof score === 'number' ? score.toFixed(1) : '0.0';
}

function getOpponentLabel(signal: Signal): string | null {
  if (!signal.opponent) return null;
  const cleaned = signal.opponent.trim();
  if (!cleaned) return null;
  const parts = cleaned.split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : cleaned;
}

function getMatchupLabel(signal: Signal): string | null {
  const opponent = getOpponentLabel(signal);
  if (!opponent) return null;
  const homeAway = signal.home_away === 'Away' || signal.home_away === '@' ? '@' : 'vs';
  const teamPrefix = signal.subject_type === 'team' ? '' : `${signal.team_name} `;
  return `${teamPrefix}${homeAway} ${opponent}`;
}

export function LastGameSignalCard({ signals, onOpenDetail }: LastGameSignalCardProps) {
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const toggleFollowPlayer = useSignalStore((state) => state.toggleFollowPlayer);
  const toggleFollowTeam = useSignalStore((state) => state.toggleFollowTeam);
  const profile = useSignalStore((state) => state.profile);

  if (!signals[0]) return null;

  const sorted = [...signals].sort(
    (a, b) => getSignalPriority(b) - getSignalPriority(a),
  );
  const primarySignal = sorted[0]!;

  const isTeamSignal = primarySignal.subject_type === 'team' || primarySignal.player_id == null;
  const isPlayerFollowed = primarySignal.player_id != null ? (profile?.follows.players.includes(primarySignal.player_id) ?? false) : false;
  const isTeamFollowed = profile?.follows.teams.includes(primarySignal.team_id) ?? false;
  const isTracked = isPlayerFollowed || isTeamFollowed;

  async function handleFollowClick(e: React.MouseEvent) {
    e.stopPropagation();
    if (!currentUser) { openAuth('signin'); return; }
    if (isTeamSignal) {
      await toggleFollowTeam(primarySignal.team_id, isTeamFollowed);
    } else if (primarySignal.player_id != null) {
      await toggleFollowPlayer(primarySignal.player_id, isPlayerFollowed);
    }
  }

  const followLabel = isTeamSignal
    ? (isTeamFollowed ? '✓ Team' : '+ Team')
    : (isPlayerFollowed ? '✓ Following' : '+ Follow');

  const primaryDirection = getSignalDirection(primarySignal);
  const isPositive = primaryDirection === 'positive';
  const isNegative = primaryDirection === 'negative';

  const borderTone = isPositive
    ? 'border-success/30 hover:border-success/55'
    : isNegative
      ? 'border-danger/30 hover:border-danger/55'
      : 'hover:border-borderStrong';

  const matchupLabel = getMatchupLabel(primarySignal);
  const result = primarySignal.game_result;
  const score = primarySignal.final_score?.replace(/\s*-\s*/g, '–') ?? null;
  const eventDate = primarySignal.event_date ? formatEventDate(primarySignal.event_date) : null;
  const resultTone =
    result === 'W'
      ? 'text-success'
      : result === 'L'
        ? 'text-danger'
        : 'text-muted';

  const subjectPath = primarySignal.subject_type === 'team'
    ? `/teams/${primarySignal.team_id}`
    : `/players/${primarySignal.player_id}`;

  return (
    <article
      className={`panel-surface select-none px-5 py-5 transition-all duration-200 hover:bg-white/[0.035] sm:px-6 sm:py-6 ${borderTone}`}
    >
      <div className="px-3 pb-2 pt-3">
        <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
          <Link to={subjectPath} className="shrink-0 max-w-full">
            <span className="block truncate text-[20px] font-bold leading-tight text-ink sm:text-[22px]">
              {primarySignal.subject_type === 'team' ? primarySignal.team_name : primarySignal.player_name}
            </span>
          </Link>
          <button
            type="button"
            onClick={(e) => void handleFollowClick(e)}
            className={`shrink-0 rounded-full border px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.16em] transition ${
              isTracked
                ? 'border-accent/30 bg-accentSoft text-accent'
                : 'border-border/60 text-muted/50 hover:border-border hover:text-muted'
            }`}
          >
            {followLabel}
          </button>
        </div>
        {matchupLabel || result || score || eventDate ? (
          <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[12px] text-muted">
            {matchupLabel ? <span>{matchupLabel}</span> : null}
            {matchupLabel && (result || score || eventDate) ? <span className="text-white/15">•</span> : null}
            {result || score ? (
              <span className="font-semibold tabular-nums">
                {result ? <span className={`${resultTone} mr-2`}>{result}</span> : null}
                {score ? <span className="text-ink/90">{score}</span> : null}
              </span>
            ) : null}
            {(result || score) && eventDate ? <span className="text-white/15">•</span> : null}
            {eventDate ? <span>{eventDate}</span> : null}
          </span>
        ) : null}
      </div>
      <div className="border-t border-white/[0.06] pt-2">
        {sorted.map((signal) => {
          const dir = getSignalDirection(signal);
          const severity = getSignalSeverity(signal);
          const deltaTone = dir === 'positive' ? 'text-green-400' : dir === 'negative' ? 'text-red-400' : 'text-white/40';
          const railTone = dir === 'positive' ? 'bg-success' : dir === 'negative' ? 'bg-danger' : 'bg-white/20';
          const formattedDelta = formatDelta(signal);
          const showArrow = dir !== 'neutral';
          const arrowChar = dir === 'positive' ? '↑' : dir === 'negative' ? '↓' : null;
          const percentLabel = typeof signal.movement_pct === 'number' ? `${signal.movement_pct >= 0 ? '+' : ''}${Math.round(signal.movement_pct)}%` : null;
          return (
            <button
              key={signal.id}
              type="button"
              onClick={() => onOpenDetail?.(signal.id)}
              className="group relative grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 rounded-[14px] border-b border-white/[0.06] px-3 py-2.5 text-left transition last:border-b-0 hover:bg-white/[0.055] focus:outline-none focus-visible:bg-white/[0.07] focus-visible:ring-1 focus-visible:ring-borderStrong"
            >
              <span className={`absolute inset-y-2 left-0 w-[3px] rounded-full opacity-70 ${railTone}`} />
              <span className="min-w-0 pl-1">
                <span className="flex min-w-0 flex-wrap items-center gap-1.5">
                  <span className="truncate text-[13px] font-semibold leading-tight text-ink sm:text-[14px]">
                    {getMetricLabel(signal)}
                  </span>
                  <span className={`rounded-full border px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[0.12em] ${getSeverityTone(severity)}`}>
                    {severity}
                  </span>
                  {signal.streak >= 2 && (
                    <span className="rounded-full border border-orange-400/30 bg-orange-400/10 px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[0.12em] text-orange-300">
                      {signal.streak}G
                    </span>
                  )}
                </span>
                <span className="mt-1 block whitespace-nowrap text-[16px] leading-none tabular-nums sm:text-[17px]">
                  <span className="font-bold text-ink">{formatStatValue(signal, signal.current_value)}</span>
                  <span className="mx-1.5 text-muted/70">vs</span>
                  <span className="font-semibold text-muted">{formatStatValue(signal, signal.baseline_value)}</span>
                </span>
                <span className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-muted">
                  <span>Delta <span className={`tabular-nums ${deltaTone}`}>{formattedDelta}</span></span>
                  <span>Z <span className="tabular-nums text-[#ffd8bd]">{formatSignedValue(signal.z_score)}</span></span>
                  <span>Score <span className="tabular-nums text-ink">{formatScore(signal)}</span></span>
                </span>
              </span>
              <span className="flex items-center justify-end gap-2">
                <span className={`flex items-baseline justify-end gap-1 whitespace-nowrap text-right tabular-nums opacity-95 ${deltaTone}`}>
                  <span className="text-[17px] font-bold leading-none tracking-tight sm:text-[19px]">
                    {percentLabel ?? formattedDelta}
                  </span>
                  {showArrow && arrowChar && <span className="text-xs leading-none" aria-hidden="true">{arrowChar}</span>}
                </span>
                <span className="flex h-6 w-6 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-muted transition group-hover:border-accent/40 group-hover:bg-accent/10 group-hover:text-[#ffd8bd]">
                  <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                    <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </article>
  );
}
