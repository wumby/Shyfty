import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { FeedToolbar } from '../components/FeedToolbar';
import { FilterDrawer } from '../components/FilterDrawer';
import { FollowingEmptyState } from '../components/FollowingEmptyState';
import { LastGameSignalCard } from '../components/LastGameSignalCard';
import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { formatEventDate } from '../lib/signalFormat';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { CascadeSignal, FeedItem, Signal, SignalFilters, SortMode } from '../types';

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
  if (typeof signal.signal_score === 'number') return signal.signal_score;
  if (typeof signal.importance === 'number') return signal.importance;
  return Math.abs(signal.z_score);
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

function isSignal(item: FeedItem): item is Signal {
  return item.type !== 'cascade';
}

function CascadeSignalCard({ cascade, onOpenDetail }: { cascade: CascadeSignal; onOpenDetail?: (signalId: number) => void }) {
  const topContributors = cascade.contributors.slice(0, 3);
  return (
    <article className="panel-surface border-sky-300/25 px-5 py-5 transition hover:border-sky-300/45 hover:bg-white/[0.035]">
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-sky-300/25 bg-sky-400/10 text-sky-200">
          ↳
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex min-w-0 flex-wrap items-center gap-2">
            <span className="truncate text-[21px] font-bold leading-tight text-ink">{cascade.trigger.player.name}</span>
            <span className="rounded-full border border-danger/30 bg-danger/10 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.16em] text-danger">
              Minutes DROP
            </span>
          </div>
          <div className="mt-1 text-[12px] text-muted">
            {cascade.team} • {formatEventDate(cascade.game_date)}
          </div>
          <div className="mt-4 text-[15px] font-semibold leading-snug text-ink">
            {cascade.narrative_summary ?? '→ Usage redistributed'}
          </div>
          <div className="mt-3 space-y-2">
            {topContributors.map((contributor) => (
              <button
                key={contributor.signal_id}
                type="button"
                onClick={() => onOpenDetail?.(contributor.signal_id)}
                className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-[14px] px-3 py-2 text-left transition hover:bg-white/[0.055]"
              >
                <span className="truncate text-sm font-semibold text-ink">{contributor.player.name}</span>
                <span className="text-sm font-bold tabular-nums text-success">
                  {contributor.delta >= 0 ? '+' : ''}{Number.isInteger(contributor.delta) ? contributor.delta.toFixed(0) : contributor.delta.toFixed(1)} {contributor.metric_label.toLowerCase()}
                </span>
              </button>
            ))}
            {cascade.contributors.length > 3 ? (
              <div className="px-3 text-xs font-semibold text-muted">+{cascade.contributors.length - 3} more</div>
            ) : null}
          </div>
        </div>
      </div>
    </article>
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
  const visibleItems = useMemo(() => {
    if (activeTab !== 'following') return signals;
    if (!profile) return [];

    return signals.filter((item) => {
      if (!isSignal(item)) {
        const triggerPlayerId = item.trigger.player.id;
        return (triggerPlayerId != null && profile.follows.players.includes(triggerPlayerId)) || profile.follows.teams.includes(item.team_id);
      }
      return (
        (item.subject_type === 'player' && item.player_id != null && profile.follows.players.includes(item.player_id)) ||
        (item.subject_type === 'team' && profile.follows.teams.includes(item.team_id))
      );
    });
  }, [activeTab, profile, signals]);
  const feedDisplayItems = useMemo(() => {
    const displays: Array<{ type: 'cascade'; cascade: CascadeSignal } | { type: 'signals'; signals: Signal[] }> = [];
    const signalOnly = visibleItems.filter(isSignal);
    const groupedSignals = groupSignalsByPlayerGame(signalOnly);
    for (const item of visibleItems) {
      if (!isSignal(item)) {
        displays.push({ type: 'cascade', cascade: item });
      }
    }
    displays.push(...groupedSignals.map((group) => ({ type: 'signals' as const, signals: group })));
    return displays;
  }, [visibleItems]);

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
            ) : visibleItems.length === 0 ? (
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
                {feedDisplayItems.map((item) => (
                  item.type === 'cascade' ? (
                    <CascadeSignalCard
                      key={item.cascade.id}
                      cascade={item.cascade}
                      onOpenDetail={(signalId) => setDetailSignalId(signalId)}
                    />
                  ) : (
                    <LastGameSignalCard
                      key={`${item.signals[0]?.player_id ?? item.signals[0]?.team_id ?? 'unknown'}-${item.signals[0]?.game_id ?? 'game'}`}
                      signals={item.signals}
                      onOpenDetail={(signalId) => setDetailSignalId(signalId)}
                    />
                  )
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
