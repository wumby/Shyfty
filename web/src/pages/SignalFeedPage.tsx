import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { FeedToolbar } from '../components/FeedToolbar';
import { FilterDrawer } from '../components/FilterDrawer';
import { FollowingEmptyState } from '../components/FollowingEmptyState';
import { LastGameSignalCard } from '../components/LastGameSignalCard';
import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { Signal, SignalFilters, SortMode } from '../types';

const LEAGUES = ['All', 'NBA', 'NFL'];
const SORTS: SortMode[] = ['newest', 'most_important', 'biggest_deviation'];

const SIGNAL_TYPE_FILTERS = [
  { label: 'All', value: 'All' },
  { label: 'Outliers', value: 'OUTLIER' },
  { label: 'Swings', value: 'SWING' },
  { label: 'Shifts', value: 'SHIFT' },
] as const;

type SignalTypeFilterValue = (typeof SIGNAL_TYPE_FILTERS)[number]['value'];
type FeedTab = 'forYou' | 'following';

function getSignalPriority(signal: Signal): number {
  if (typeof signal.importance === 'number') return signal.importance;
  const severityRank = signal.severity === 'OUTLIER' ? 3 : signal.severity === 'SWING' ? 2 : 1;
  return severityRank * 100 + (signal.deviation ?? Math.abs(signal.z_score));
}

function groupSignalsByPlayerGame(signals: Signal[]): Signal[][] {
  const grouped = new Map<string, Signal[]>();

  for (const signal of signals) {
    const key = `${signal.subject_type ?? 'player'}:${signal.player_id ?? signal.team_id}:${signal.game_id}`;
    const existing = grouped.get(key);
    if (existing) {
      existing.push(signal);
    } else {
      grouped.set(key, [signal]);
    }
  }

  return [...grouped.values()].map((group) =>
    [...group].sort(
      (left, right) => getSignalPriority(right) - getSignalPriority(left),
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
  const { filters, signals, loadingInitial, loadingMore, hasMore, ingestStatus, setFilters, fetchSignals, loadMore, fetchProfile, profile } = useSignalStore();
  const currentUser = useAuthStore((state) => state.currentUser);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  const tabFromUrl = searchParams.get('tab') ?? 'forYou';
  const activeTab: FeedTab = tabFromUrl === 'following' ? 'following' : 'forYou';

  const leagueFromUrl = searchParams.get('league') ?? 'All';
  const activeLeague = LEAGUES.includes(leagueFromUrl) ? leagueFromUrl : 'All';
  const signalTypeFromUrl = searchParams.get('signal_type') ?? 'All';
  const activeSignalType = (SIGNAL_TYPE_FILTERS.some((f) => f.value === signalTypeFromUrl)
    ? signalTypeFromUrl
    : 'All') as SignalTypeFilterValue;
  const sortFromUrl = searchParams.get('sort') as SortMode | null;
  const activeSort = sortFromUrl && SORTS.includes(sortFromUrl) ? sortFromUrl : 'newest';
  const followingHasFollows =
    (profile?.follows.players.length ?? 0) > 0 ||
    (profile?.follows.teams.length ?? 0) > 0;
  const visibleSignals = useMemo(() => {
    if (activeTab !== 'following') return signals;
    if (!profile) return [];

    return signals.filter(
      (signal) =>
        (signal.player_id != null && profile.follows.players.includes(signal.player_id)) ||
        profile.follows.teams.includes(signal.team_id),
    );
  }, [activeTab, profile, signals]);
  const groupedSignals = groupSignalsByPlayerGame(visibleSignals);

  const activeFilters = useMemo<SignalFilters>(
    () => ({
      league: activeLeague === 'All' ? undefined : activeLeague,
      signal_type: activeSignalType === 'All' ? undefined : activeSignalType,
      sort: activeSort,
      feed: activeTab === 'following' ? 'following' : 'all',
    }),
    [activeLeague, activeSignalType, activeSort, activeTab],
  );

  useEffect(() => {
    setFilters(activeFilters);
  }, [activeFilters, setFilters]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals, filters]);

  useEffect(() => {
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  function handleTabChange(tab: FeedTab) {
    const params = new URLSearchParams(searchParams);
    if (tab === 'following') {
      params.set('tab', 'following');
    } else {
      params.delete('tab');
    }
    setSearchParams(params, { replace: true });
    setFiltersOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function updateParams(next: SignalFilters) {
    const params = new URLSearchParams(searchParams);
    if (!next.league) {
      params.delete('league');
    } else {
      params.set('league', next.league);
    }

    if (!next.signal_type) {
      params.delete('signal_type');
    } else {
      params.set('signal_type', next.signal_type);
    }

    if (!next.sort || next.sort === 'newest') {
      params.delete('sort');
    } else {
      params.set('sort', next.sort);
    }

    setSearchParams(params, { replace: true });
  }

  function removeFilter(key: 'league' | 'signal_type' | 'sort') {
    updateParams({
      ...activeFilters,
      [key]: key === 'sort' ? 'newest' : undefined,
    });
  }

  return (
    <>
      <div className="flex max-w-[1540px] min-w-0 flex-col gap-6 transition-[padding] duration-300 lg:flex-row lg:items-start">
        {activeTab === 'forYou' ? (
          <FilterDrawer
            open={filtersOpen}
            filters={activeFilters}
            onChange={updateParams}
            onClose={() => setFiltersOpen(false)}
          />
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="sticky top-16 z-40">
            <FeedToolbar
              filters={activeFilters}
              filtersOpen={filtersOpen}
              onOpenFilters={() => setFiltersOpen(true)}
              onRemoveFilter={removeFilter}
              aside={<FreshnessBar />}
              activeTab={activeTab}
              onTabChange={handleTabChange}
            />
            <div className="h-5 bg-gradient-to-b from-bg to-transparent backdrop-blur-md" />
          </div>

          <section className="space-y-4">
            {loadingInitial ? (
              <LoadingState />
            ) : activeTab === 'following' && profile !== null && !followingHasFollows ? (
              <FollowingEmptyState />
            ) : visibleSignals.length === 0 ? (
              activeTab === 'following' ? (
                <FollowingEmptyState />
              ) : (
                <div className="rounded-[22px] border border-white/[0.07] bg-white/[0.025] px-4 py-10 text-center text-sm text-muted">
                  {ingestStatus?.last_updated
                    ? 'No last-game signals are available for this view yet.'
                    : 'No real data has been synced yet. Run a bootstrap or incremental sync to build the live signal board.'}
                </div>
              )
            ) : (
              <>
                {groupedSignals.map((signalGroup) => (
                  <LastGameSignalCard
                    key={`${signalGroup[0]?.player_id ?? signalGroup[0]?.team_id ?? 'unknown'}-${signalGroup[0]?.game_id ?? 'game'}`}
                    signals={signalGroup}
                    onOpenDetail={(signalId) => setDetailSignalId(signalId)}
                  />
                ))}
                {hasMore && activeTab === 'forYou' ? (
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
      </div>

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </>
  );
}
