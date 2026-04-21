import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { LastGameSignalCard } from '../components/LastGameSignalCard';
import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
import { SectionHeader } from '../components/SectionHeader';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { useSignalStore } from '../store/useSignalStore';
import type { Signal } from '../types';

const LEAGUES = ['All', 'NBA', 'NFL'];
const SIGNAL_TYPES = ['All', 'OUTLIER', 'SPIKE', 'DROP', 'SHIFT'] as const;

function groupSignalsByPlayerGame(signals: Signal[]): Signal[][] {
  const grouped = new Map<string, Signal[]>();

  for (const signal of signals) {
    const key = `${signal.player_id}:${signal.game_id}`;
    const existing = grouped.get(key);
    if (existing) {
      existing.push(signal);
    } else {
      grouped.set(key, [signal]);
    }
  }

  return [...grouped.values()].map((group) =>
    [...group].sort(
      (left, right) => Math.abs(right.current_value - right.baseline_value) - Math.abs(left.current_value - left.baseline_value),
    ),
  );
}

function FreshnessBar() {
  const { ingestStatus, fetchIngestStatus } = useSignalStore();
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void fetchIngestStatus();
    pollRef.current = setInterval(() => void fetchIngestStatus(), 60000);
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [fetchIngestStatus]);

  if (!ingestStatus?.last_updated) return null;

  const stale = Date.now() - new Date(ingestStatus.last_updated).getTime() > 6 * 60 * 60 * 1000;
  const dotTone =
    ingestStatus.status === 'running'
      ? 'bg-amber-400 animate-pulse'
      : stale || ingestStatus.status === 'error'
        ? 'bg-danger'
        : 'bg-success';

  return (
    <div className="flex items-center gap-2 text-sm text-muted">
      <span className={`inline-block h-2 w-2 rounded-full ${dotTone}`} />
      <span>{stale ? 'Board may be stale' : 'Updated recently'}</span>
    </div>
  );
}

export function SignalFeedPage() {
  const { filters, signals, loadingInitial, loadingMore, hasMore, setFilters, fetchSignals, loadMore } = useSignalStore();
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();

  const leagueFromUrl = searchParams.get('league') ?? 'All';
  const activeLeague = LEAGUES.includes(leagueFromUrl) ? leagueFromUrl : 'All';
  const signalTypeFromUrl = searchParams.get('signal_type') ?? 'All';
  const activeSignalType = SIGNAL_TYPES.includes(signalTypeFromUrl as (typeof SIGNAL_TYPES)[number])
    ? signalTypeFromUrl
    : 'All';
  const groupedSignals = groupSignalsByPlayerGame(signals);

  useEffect(() => {
    setFilters({
      league: activeLeague === 'All' ? undefined : activeLeague,
      signal_type: activeSignalType === 'All' ? undefined : activeSignalType,
      sort: 'newest',
      feed: 'all',
    });
  }, [activeLeague, activeSignalType, setFilters]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals, filters]);

  function updateParams(next: { league?: string; signal_type?: string }) {
    const params = new URLSearchParams(searchParams);
    if (!next.league || next.league === 'All') {
      params.delete('league');
    } else {
      params.set('league', next.league);
    }

    if (!next.signal_type || next.signal_type === 'All') {
      params.delete('signal_type');
    } else {
      params.set('signal_type', next.signal_type);
    }

    setSearchParams(params, { replace: true });
  }

  return (
    <>
      <div className="flex min-w-0 flex-col gap-4">
        <PageIntro
          eyebrow="Last-Game Feed"
          title="Feed"
          description="Easy-to-read player signals from the most recent game played. Scan the player, the stat that stood out, and the game context."
          aside={<FreshnessBar />}
        />

        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Last-Game Signals"
            description="Start with the latest signals below. Each card shows who stood out, what happened in the last game, and who they played."
          />

          <div className="mt-4 flex flex-wrap gap-2">
            {LEAGUES.map((league) => (
              <button
                key={league}
                type="button"
                onClick={() => updateParams({ league, signal_type: activeSignalType })}
                className={`pill-button ${activeLeague === league ? 'pill-button-active' : ''}`}
              >
                {league}
              </button>
            ))}
          </div>

          <div className="mt-3 flex flex-wrap gap-2">
            {SIGNAL_TYPES.map((signalType) => (
              <button
                key={signalType}
                type="button"
                onClick={() => updateParams({ league: activeLeague, signal_type: signalType })}
                className={`pill-button ${activeSignalType === signalType ? 'pill-button-active' : ''}`}
              >
                {signalType === 'All'
                  ? 'All Types'
                  : signalType.charAt(0) + signalType.slice(1).toLowerCase()}
              </button>
            ))}
          </div>
        </section>

        <section className="space-y-3">
          {loadingInitial ? (
            <LoadingState />
          ) : signals.length === 0 ? (
            <div className="panel-surface px-4 py-8 text-center text-sm text-muted">
              No last-game signals are available for this view yet.
            </div>
          ) : (
            <>
              {groupedSignals.map((signalGroup) => (
                <LastGameSignalCard
                  key={`${signalGroup[0]?.player_id ?? 'player'}-${signalGroup[0]?.game_id ?? 'game'}`}
                  signals={signalGroup}
                  onOpenDetail={(signalId) => setDetailSignalId(signalId)}
                />
              ))}
              {hasMore ? (
                <button
                  type="button"
                  onClick={() => void loadMore()}
                  className="mx-auto block rounded-full border border-border bg-white/[0.03] px-5 py-2.5 text-sm font-semibold text-muted transition hover:border-borderStrong hover:text-ink"
                >
                  {loadingMore ? 'Loading…' : 'Load more'}
                </button>
              ) : null}
            </>
          )}
        </section>
      </div>

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </>
  );
}
