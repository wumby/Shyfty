import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LastGameSignalCard } from '../components/LastGameSignalCard';
import { LoadingState } from '../components/LoadingState';
import { SectionHeader } from '../components/SectionHeader';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { api } from '../services/api';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { PlayerBoxScore, PlayerDetail, Signal } from '../types';
import { formatGameContext, formatSignalLabel } from '../lib/signalFormat';

function groupSignalsByGame(signals: Signal[]): Signal[][] {
  const grouped = new Map<string | number, Signal[]>();
  for (const signal of signals) {
    const key = signal.game_id ?? signal.event_date ?? 'unknown';
    const existing = grouped.get(key);
    if (existing) existing.push(signal);
    else grouped.set(key, [signal]);
  }
  return [...grouped.values()];
}

const PLAYER_BOX_SCORE_FIELDS: Array<[keyof PlayerBoxScore, string, 'number' | 'percent']> = [
  ['points', 'PTS', 'number'],
  ['rebounds', 'REB', 'number'],
  ['assists', 'AST', 'number'],
  ['minutes_played', 'MIN', 'number'],
  ['usage_rate', 'USG', 'percent'],
  ['steals', 'STL', 'number'],
  ['blocks', 'BLK', 'number'],
  ['turnovers', 'TO', 'number'],
  ['plus_minus', '+/-', 'number'],
  ['fg_pct', 'FG%', 'percent'],
  ['fg3_pct', '3P%', 'percent'],
  ['ft_pct', 'FT%', 'percent'],
  ['passing_yards', 'PASS YDS', 'number'],
  ['rushing_yards', 'RUSH YDS', 'number'],
  ['receiving_yards', 'REC YDS', 'number'],
  ['touchdowns', 'TD', 'number'],
];

function formatBoxScoreValue(value: number, mode: 'number' | 'percent') {
  if (mode === 'percent') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    return `${Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1)}%`;
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function PlayerBoxScores({ rows }: { rows: PlayerBoxScore[] }) {
  return (
    <section className="panel-surface px-4 py-4">
      <div className="flex items-center justify-between gap-3 px-1">
        <h2 className="text-base font-semibold text-ink">Last 5 Box Scores</h2>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">{rows.length}/5 games</span>
      </div>
      <div className="mt-3 space-y-2">
        {rows.length === 0 ? (
          <div className="rounded-[16px] border border-dashed border-borderStrong bg-white/[0.025] px-4 py-4 text-sm text-muted">
            No box scores are stored for this player yet.
          </div>
        ) : rows.map((row) => {
          const stats = PLAYER_BOX_SCORE_FIELDS
            .map(([key, label, mode]) => {
              const value = row[key];
              return typeof value === 'number' ? { label, value: formatBoxScoreValue(value, mode) } : null;
            })
            .filter(Boolean) as Array<{ label: string; value: string }>;
          return (
            <div key={row.game_id} className="rounded-[16px] border border-border bg-white/[0.025] px-3 py-3">
              <div className="grid gap-3 lg:grid-cols-[170px_minmax(0,1fr)] lg:items-center">
                <div className="min-w-0 border-b border-border pb-2 lg:border-b-0 lg:border-r lg:pb-0 lg:pr-3">
                  <div className="truncate text-sm font-semibold text-ink">
                    {row.home_away === 'Away' ? '@' : 'vs'} {row.opponent}
                  </div>
                  <div className="mt-0.5 truncate text-[11px] text-muted">{formatGameContextDate(row.game_date)}{row.season ? ` · ${row.season}` : ''}</div>
                </div>
                <div className="grid grid-cols-[repeat(auto-fit,minmax(64px,1fr))] gap-px overflow-hidden rounded-[12px] border border-border bg-border">
                  {stats.map((stat) => (
                    <div key={`${row.game_id}-${stat.label}`} className="min-w-0 bg-[#081421] px-2.5 py-2">
                      <div className="truncate text-[8px] font-semibold uppercase tracking-[0.1em] text-muted">{stat.label}</div>
                      <div className="mt-0.5 truncate text-xs font-semibold tabular-nums text-ink">{stat.value}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function formatGameContextDate(value: string) {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
      .format(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))));
  }
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

export function PlayerDetailPage() {
  const { id = '' } = useParams();
  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);
  const toggleFollowPlayer = useSignalStore((s) => s.toggleFollowPlayer);
  const profile = useSignalStore((s) => s.profile);
  const fetchProfile = useSignalStore((s) => s.fetchProfile);

  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [playerRes, signalRes] = await Promise.all([
          api.getPlayer(id),
          api.getPlayerSignals(id),
        ]);
        setPlayer(playerRes);
        setSignals(signalRes);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id]);

  const primarySignal = signals[0] ?? null;
  const groupedSignals = useMemo(() => groupSignalsByGame(signals), [signals]);
  const contextCards = useMemo(
    () => [
      { label: 'Team', value: player?.team_name ?? '—' },
      { label: 'League', value: player?.league_name ?? '—' },
      { label: 'Active Signals', value: String(signals.length) },
      { label: 'Latest Signal', value: primarySignal ? formatSignalLabel(primarySignal.severity ?? primarySignal.signal_type) : 'None yet' },
    ],
    [player, primarySignal, signals.length],
  );

  if (loading) return <LoadingState />;
  if (error || !player) return <EmptyState title="Player unavailable" copy={error ?? 'No player found.'} />;

  const isFollowed = profile?.follows.players.includes(player.id) ?? player.is_followed;

  async function handleFollow() {
    if (!currentUser) { openAuth('signin'); return; }
    await toggleFollowPlayer(player!.id, isFollowed);
  }

  return (
    <>
      <div className="space-y-4">
        <section className="panel-surface px-5 py-5 sm:px-6">
          <nav className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            <Link to="/players" className="transition hover:text-ink">Players</Link>
            <span className="text-white/20">/</span>
            <span className="text-ink">{player.name}</span>
          </nav>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <div className="eyebrow">{player.league_name}</div>
              <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">{player.name}</h1>
              <p className="mt-1.5 text-sm text-muted">{player.team_name} · {player.position}</p>
              {isFollowed ? (
                <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-accent/35 bg-accentSoft px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#ffe2cb]">
                  <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_16px_rgba(249,115,22,0.7)]" />
                  Tracking
                </div>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => void handleFollow()}
              className={`shrink-0 rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                isFollowed
                  ? 'border-accent/40 bg-accentSoft text-accent hover:bg-accent/20'
                  : 'border-border bg-white/[0.04] text-muted hover:border-borderStrong hover:text-ink'
              }`}
            >
              {isFollowed ? '✓ Following' : '+ Follow'}
            </button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {contextCards.map((card) => (
              <div key={card.label} className="rounded-[20px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{card.label}</div>
                <div className="mt-2 text-xl font-semibold text-ink">{card.value}</div>
              </div>
            ))}
          </div>
        </section>

        <PlayerBoxScores rows={player.recent_box_scores} />

        {primarySignal ? (
          <section className="panel-surface px-4 py-4">
            <SectionHeader
              title="Latest Context"
              description="The most recent signal is the anchor. Everything else here should help explain that moment."
            />
            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)]">
              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="eyebrow">Current Signal</div>
                <div className="mt-2 text-2xl font-semibold text-ink">
                  {formatSignalLabel(primarySignal.severity ?? primarySignal.signal_type)} on {primarySignal.metric_label ?? primarySignal.metric_name}
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">{primarySignal.explanation}</p>
                <div className="mt-3 text-sm text-[#ffd8bd]">{formatGameContext(primarySignal)}</div>
              </div>
              <div className="rounded-[22px] border border-border bg-[#09172a]/80 px-4 py-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Why it surfaced</div>
                <div className="mt-3 flex items-end justify-between gap-3">
                  <div>
                    <div className="text-xs text-muted">Current</div>
                    <div className="text-2xl font-semibold text-ink">{primarySignal.current_value}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Baseline</div>
                    <div className="text-xl font-semibold text-ink">{primarySignal.baseline_value}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Z-score</div>
                    <div className="text-xl font-semibold text-[#ffd8bd]">{primarySignal.z_score.toFixed(1)}</div>
                  </div>
                </div>
                <div className="mt-4 text-xs leading-5 text-muted">
                  Supporting context is intentionally tight here: enough to explain the signal, not enough to turn this page into a long-range stats encyclopedia.
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Recent Signals"
            description="Read the active signals first. If this list is empty, the player simply does not have a fresh signal yet."
            aside={<div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{signals.length} total</div>}
          />

          <div className="mt-4 space-y-4">
            {groupedSignals.length === 0 ? (
              <div className="rounded-[20px] border border-dashed border-borderStrong bg-white/[0.03] px-4 py-5 text-sm text-muted">
                No recent signals are active for this player yet. This page will fill in once the next real-data sync produces signal-worthy movement.
              </div>
            ) : (
              groupedSignals.map((group) => (
                <LastGameSignalCard
                  key={`${group[0]?.player_id ?? group[0]?.team_id ?? 'unknown'}-${group[0]?.game_id ?? group[0]?.event_date ?? 'game'}`}
                  signals={group}
                  onOpenDetail={(signalId) => setDetailSignalId(signalId)}
                />
              ))
            )}
          </div>
        </section>
      </div>

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </>
  );
}
