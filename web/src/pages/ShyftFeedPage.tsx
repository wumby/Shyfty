import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { FeedToolbar } from '../components/FeedToolbar';
import { FilterDrawer } from '../components/FilterDrawer';
import { FollowingEmptyState } from '../components/FollowingEmptyState';
import { LastGameShyftCard } from "../components/LastGameShyftCard";
import { LoadingState } from '../components/LoadingState';
import { ShyftCommentsDrawer } from "../components/ShyftCommentsDrawer";
import { ShyftDetailDrawer } from "../components/ShyftDetailDrawer";
import { formatEventDate } from "../lib/shyftFormat";
import { useAuthStore } from '../store/useAuthStore';
import { useShyftStore } from "../store/useShyftStore";
import type { CascadeShyft, FeedItem, Shyft, ShyftFilters, SortMode } from '../types';

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
type CommentThread = {
  shyftId: number;
  shyftIds: number[];
  title: string;
  subtitle?: string;
  gameResult?: string | null;
  finalScore?: string | null;
};

function getSignalPriority(signal: Shyft): number {
  if (typeof signal.shyft_score === 'number') return signal.shyft_score;
  if (typeof signal.importance === 'number') return signal.importance;
  return Math.abs(signal.z_score);
}

function groupSignalsByPlayerGame(signals: Shyft[]): Shyft[][] {
  const grouped = new Map<string, Shyft[]>();

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

function isSignal(item: FeedItem): item is Shyft {
  return item.type !== 'cascade';
}

function CascadeShyftCard({ cascade, onOpenDetail }: { cascade: CascadeShyft; onOpenDetail?: (shyftId: number) => void }) {
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
                key={contributor.shyft_id}
                type="button"
                onClick={() => onOpenDetail?.(contributor.shyft_id)}
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

export function ShyftFeedPage() {
  const { filters, shyfts, loadingInitial, loadingMore, hasMore, ingestStatus, setFilters, fetchShyfts, loadMore, fetchProfile, profile } = useShyftStore();
  const setShyftGroupCommentCount = useShyftStore((state) => state.setShyftGroupCommentCount);
  const currentUser = useAuthStore((state) => state.currentUser);
  const [detailShyftId, setDetailShyftId] = useState<number | null>(null);
  const [commentThread, setCommentThread] = useState<CommentThread | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    function onScroll() { setScrolled(window.scrollY > 8); }
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const tabFromUrl = searchParams.get('tab') ?? 'forYou';
  const activeTab: FeedTab = tabFromUrl === 'following' ? 'following' : 'forYou';

  const leagueFromUrl = searchParams.get('league') ?? 'All';
  const activeLeague = LEAGUES.includes(leagueFromUrl) ? leagueFromUrl : 'All';
  const signalTypeFromUrl = searchParams.get('shyft_type') ?? 'All';
  const activeSignalType = (SIGNAL_TYPE_FILTERS.some((f) => f.value === signalTypeFromUrl)
    ? signalTypeFromUrl
    : 'All') as SignalTypeFilterValue;
  const sortFromUrl = searchParams.get('sort') as SortMode | null;
  const activeSort = sortFromUrl && SORTS.includes(sortFromUrl) ? sortFromUrl : 'newest';
  const followedPlayers = profile?.follows?.players ?? [];
  const followedTeams = profile?.follows?.teams ?? [];
  const followingHasFollows =
    followedPlayers.length > 0 ||
    followedTeams.length > 0;
  const visibleItems = useMemo(() => {
    if (activeTab !== 'following') return shyfts;
    if (!profile) return [];

    return shyfts.filter((item) => {
      if (!isSignal(item)) {
        const triggerPlayerId = item.trigger.player.id;
        return (triggerPlayerId != null && followedPlayers.includes(triggerPlayerId)) || followedTeams.includes(item.team_id);
      }
      return (
        (item.subject_type === 'player' && item.player_id != null && followedPlayers.includes(item.player_id)) ||
        (item.subject_type === 'team' && followedTeams.includes(item.team_id))
      );
    });
  }, [activeTab, followedPlayers, followedTeams, profile, shyfts]);
  const feedDisplayItems = useMemo(() => {
    const displays: Array<{ type: 'cascade'; cascade: CascadeShyft } | { type: 'shyfts'; shyfts: Shyft[] }> = [];
    const signalOnly = visibleItems.filter(isSignal);
    const groupedSignals = groupSignalsByPlayerGame(signalOnly);
    for (const item of visibleItems) {
      if (!isSignal(item)) {
        displays.push({ type: 'cascade', cascade: item });
      }
    }
    displays.push(...groupedSignals.map((group) => ({ type: 'shyfts' as const, shyfts: group })));
    return displays;
  }, [visibleItems]);

  const activeFilters = useMemo<ShyftFilters>(
    () => ({
      league: activeLeague === 'All' ? undefined : activeLeague,
      shyft_type: activeSignalType === 'All' ? undefined : activeSignalType,
      sort: activeSort,
      feed: activeTab === 'following' ? 'following' : 'all',
    }),
    [activeLeague, activeSignalType, activeSort, activeTab],
  );

  useEffect(() => {
    setFilters(activeFilters);
  }, [activeFilters, setFilters]);

  useEffect(() => {
    void fetchShyfts();
  }, [fetchShyfts, filters]);

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

  function updateParams(next: ShyftFilters) {
    const params = new URLSearchParams(searchParams);
    if (!next.league) {
      params.delete('league');
    } else {
      params.set('league', next.league);
    }

    if (!next.shyft_type) {
      params.delete('shyft_type');
    } else {
      params.set('shyft_type', next.shyft_type);
    }

    if (!next.sort || next.sort === 'newest') {
      params.delete('sort');
    } else {
      params.set('sort', next.sort);
    }

    setSearchParams(params, { replace: true });
  }

  function removeFilter(key: 'league' | 'shyft_type' | 'sort') {
    updateParams({
      ...activeFilters,
      [key]: key === 'sort' ? 'newest' : undefined,
    });
  }

  return (
    <>
      <div className="flex w-full min-w-0 flex-col gap-6 transition-[padding] duration-300 lg:flex-row lg:items-start">
        {activeTab === 'forYou' ? (
          <FilterDrawer
            open={filtersOpen}
            filters={activeFilters}
            onChange={updateParams}
            onClose={() => setFiltersOpen(false)}
          />
        ) : null}

        <div className="min-w-0 flex-1">
          <div className={`sticky top-16 z-40 -mx-4 px-4 transition-[background-color,border-color,box-shadow] sm:-mx-6 sm:px-6 ${scrolled ? 'border-b border-white/[0.07] bg-[#07111f]/90 shadow-sm backdrop-blur-xl' : ''}`}>
            <FeedToolbar
              filters={activeFilters}
              filtersOpen={filtersOpen}
              onOpenFilters={() => setFiltersOpen(true)}
              onRemoveFilter={removeFilter}
              activeTab={activeTab}
              onTabChange={handleTabChange}
            />
          </div>

          <section className="space-y-4 pt-4">
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
                    ? 'No last-game shyfts are available for this view yet.'
                    : 'No real data has been synced yet. Run a bootstrap or incremental sync to build the live shyft board.'}
                </div>
              )
            ) : (
              <>
                {feedDisplayItems.map((item) => (
                  item.type === 'cascade' ? (
                    <CascadeShyftCard
                      key={item.cascade.id}
                      cascade={item.cascade}
                      onOpenDetail={(shyftId) => setDetailShyftId(shyftId)}
                    />
                  ) : (
                    <LastGameShyftCard
                      key={`${item.shyfts[0]?.player_id ?? item.shyfts[0]?.team_id ?? 'unknown'}-${item.shyfts[0]?.game_id ?? 'game'}`}
                      shyfts={item.shyfts}
                      onOpenDetail={(shyftId) => setDetailShyftId(shyftId)}
                      onOpenComments={(shyftId, title, subtitle, shyftIds, extra) =>
                        setCommentThread({ shyftId, title, subtitle, shyftIds: shyftIds?.length ? shyftIds : [shyftId], ...extra })
                      }
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

      {detailShyftId != null ? (
        <ShyftDetailDrawer shyftId={detailShyftId} onClose={() => setDetailShyftId(null)} />
      ) : null}
      {commentThread ? (
        <ShyftCommentsDrawer
          shyftId={commentThread.shyftId}
          title={commentThread.title}
          subtitle={commentThread.subtitle}
          gameResult={commentThread.gameResult}
          finalScore={commentThread.finalScore}
          onCountChange={(count) => setShyftGroupCommentCount(commentThread.shyftIds, count)}
          onClose={() => setCommentThread(null)}
        />
      ) : null}
    </>
  );
}
