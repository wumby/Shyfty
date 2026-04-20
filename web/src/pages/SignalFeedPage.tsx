import { useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';

import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { SignalFeed } from '../components/SignalFeed';
import { SignalsPageHeader } from '../components/SignalsPageHeader';
import { SignalsToolbar } from '../components/SignalsToolbar';
import { TrendingSection } from '../components/TrendingSection';
import { formatDelta, formatRelativeTime, getSignalMomentum, getSignalDirection } from '../lib/signalFormat';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { FeedMode, SortMode } from '../types';

const SAVED_VIEW_KEY = 'shyfty_saved_view';
const PREFERRED_FEED_KEY = 'shyfty_preferred_feed_mode';

function formatRefreshLabel(lastUpdated: string | null): string {
  if (!lastUpdated) return 'Not yet refreshed';
  const diff = Date.now() - new Date(lastUpdated).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Refreshed just now';
  if (mins < 60) return `Refreshed ${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Refreshed ${hrs}h ago`;
  return `Refreshed ${Math.floor(hrs / 24)}d ago`;
}

function FreshnessBar() {
  const { ingestStatus, fetchIngestStatus, triggerIngest } = useSignalStore();
  const currentUser = useAuthStore((s) => s.currentUser);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    void fetchIngestStatus();
    pollRef.current = setInterval(
      () => void fetchIngestStatus(),
      ingestStatus?.status === 'running' ? 5000 : 60000,
    );
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchIngestStatus, ingestStatus?.status]);

  if (!ingestStatus) return null;

  const stale = ingestStatus.last_updated
    ? Date.now() - new Date(ingestStatus.last_updated).getTime() > 6 * 60 * 60 * 1000
    : true;
  const dotColor =
    ingestStatus.status === 'running'
      ? 'bg-amber-400 animate-pulse'
      : ingestStatus.status === 'error' || stale
        ? 'bg-danger'
        : 'bg-success';

  const label =
    ingestStatus.status === 'running'
      ? 'Daily refresh in progress…'
      : ingestStatus.status === 'error'
        ? 'Last refresh failed'
        : stale
          ? `Board stale · ${formatRefreshLabel(ingestStatus.last_updated)}`
          : formatRefreshLabel(ingestStatus.last_updated);

  return (
    <div className="flex flex-col items-end gap-1.5 text-[11px] text-muted">
      <div className="flex items-center gap-2">
        <span className={`inline-block h-2 w-2 rounded-full ${dotColor}`} />
        <span>{label}</span>
        {currentUser != null && ingestStatus.status !== 'running' && (
          <button
            type="button"
            onClick={() => void triggerIngest()}
            className="ml-1 rounded-full border border-border bg-white/[0.03] px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted/80 transition hover:border-borderStrong hover:text-ink"
          >
            Refresh now
          </button>
        )}
      </div>
      {ingestStatus.last_error ? <div className="max-w-[320px] text-right text-[10px] text-danger">{ingestStatus.last_error}</div> : null}
    </div>
  );
}

export function SignalFeedPage() {
  const {
    filters,
    signals,
    loadingInitial,
    hasMore,
    players,
    setFilters,
    fetchSignals,
    fetchPlayers,
    feedContext,
    profile,
    fetchProfile,
    saveView,
    ingestStatus,
  } = useSignalStore();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const hydratedRef = useRef(false);
  const personalizedDefaultRef = useRef(false);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    if (hydratedRef.current) return;
    hydratedRef.current = true;

    const urlLeague = searchParams.get('league') ?? undefined;
    const urlType = searchParams.get('signal_type') ?? undefined;
    const urlPlayer = searchParams.get('player') ?? undefined;
    const urlSort = (searchParams.get('sort') as SortMode | null) ?? undefined;
    const urlFeed = (searchParams.get('feed') as FeedMode | null) ?? undefined;

    if (urlLeague || urlType || urlPlayer || urlSort || urlFeed) {
      setFilters({ league: urlLeague, signal_type: urlType, player: urlPlayer, sort: urlSort ?? 'newest', feed: urlFeed ?? 'all' });
    } else {
      try {
        const saved = localStorage.getItem(SAVED_VIEW_KEY);
        if (saved) {
          setFilters(JSON.parse(saved));
          return;
        }

        const preferredFeed = localStorage.getItem(PREFERRED_FEED_KEY) as FeedMode | null;
        if (preferredFeed === 'following' || preferredFeed === 'all' || preferredFeed === 'for_you') {
          setFilters({ sort: 'newest', feed: preferredFeed });
        }
      } catch {
        // ignore parse errors
      }
    }
  }, [searchParams, setFilters]);

  useEffect(() => {
    if (personalizedDefaultRef.current) return;
    if (searchParams.get('feed')) return;
    if (!profile) return;
    const hasFollows = profile.follows.players.length + profile.follows.teams.length > 0;
    if (!hasFollows) return;

    personalizedDefaultRef.current = true;

    try {
      const preferredFeed = localStorage.getItem(PREFERRED_FEED_KEY);
      if (!preferredFeed) {
        localStorage.setItem(PREFERRED_FEED_KEY, 'following');
      }
    } catch {
      // ignore
    }

    if ((filters.feed ?? 'all') === 'all') {
      setFilters({ ...filters, feed: 'following' });
    }
  }, [filters, profile, searchParams, setFilters]);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (filters.league) params.league = filters.league;
    if (filters.signal_type) params.signal_type = filters.signal_type;
    if (filters.player) params.player = filters.player;
    if (filters.sort) params.sort = filters.sort;
    if (filters.feed) params.feed = filters.feed;
    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  useEffect(() => {
    try {
      localStorage.setItem(PREFERRED_FEED_KEY, filters.feed ?? 'all');
    } catch {
      // ignore
    }
  }, [filters.feed]);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals, filters]);

  useEffect(() => {
    if (players.length === 0) void fetchPlayers();
  }, [fetchPlayers, players.length]);

  function handleSaveView() {
    try {
      localStorage.setItem(SAVED_VIEW_KEY, JSON.stringify(filters));
    } catch {
      // ignore
    }
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    const name = window.prompt('Name this saved view');
    if (name?.trim()) void saveView(name.trim());
  }

  const leagueLabel = filters.league ?? 'All leagues';
  const typeLabel = filters.signal_type ?? 'All signals';
  const countLabel = `${signals.length}${hasMore ? '+' : ''} signals`;
  const hasActiveFilters = !!(filters.league || filters.signal_type || filters.player || filters.feed !== 'all' || filters.sort !== 'newest');
  const stale = ingestStatus?.last_updated ? Date.now() - new Date(ingestStatus.last_updated).getTime() > 6 * 60 * 60 * 1000 : false;
  const hasFollows = (profile?.follows.players.length ?? 0) + (profile?.follows.teams.length ?? 0) > 0;
  const rankedSignals = [...signals]
    .map((signal) => ({
      signal,
      score: getSignalMomentum(
        signal,
        Boolean(profile?.follows.players.includes(signal.player_id) || profile?.follows.teams.includes(signal.team_id)),
        feedContext?.sort_mode,
      ),
    }))
    .sort((left, right) => right.score - left.score);
  const topSignals = rankedSignals.slice(0, 1).map(({ signal }) => signal);
  const feedSignals = topSignals.length ? signals.filter((signal) => !topSignals.some((topSignal) => topSignal.id === signal.id)) : signals;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-3">
        <div className="flex items-start justify-between gap-3">
          <SignalsPageHeader leagueLabel={leagueLabel} typeLabel={typeLabel} countLabel={countLabel} />
          <div className="flex shrink-0 flex-col items-end gap-2 pt-1">
            <FreshnessBar />
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleSaveView}
                className="rounded-full border border-border bg-white/[0.03] px-2.5 py-1 text-[10px] uppercase tracking-[0.14em] text-muted/70 transition hover:border-borderStrong hover:text-ink"
              >
                Save view
              </button>
            )}
          </div>
        </div>

        {stale ? (
          <div className="rounded-[22px] border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-[#f2c1c1]">
            Board freshness is weak. Use the live board directionally until the next ingest completes.
          </div>
        ) : null}

        {profile?.saved_views.length ? (
          <section className="panel-surface px-4 py-3">
            <div className="eyebrow mb-2">Saved Views</div>
            <div className="flex flex-wrap gap-2">
              {profile.saved_views.slice(0, 4).map((view) => (
                <button
                  key={view.id}
                  type="button"
                  onClick={() => setFilters({
                    league: view.league ?? undefined,
                    signal_type: view.signal_type ?? undefined,
                    player: view.player ?? undefined,
                    sort: view.sort_mode,
                    feed: view.feed_mode,
                  })}
                  className="rounded-full border border-border bg-white/[0.03] px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-ink"
                >
                  {view.name}
                </button>
              ))}
            </div>
          </section>
        ) : null}

        <SignalsToolbar
          filters={filters}
          players={players}
          signalCount={signals.length}
          hasMore={hasMore}
          filtersOpen={filtersOpen}
          onOpenFilters={() => setFiltersOpen(true)}
          onCloseFilters={() => setFiltersOpen(false)}
          onChangeFilters={(nextFilters) => setFilters(nextFilters)}
        />

        {hasFollows && (filters.feed ?? 'all') === 'following' ? (
          <div className="rounded-[22px] border border-accent/30 bg-accentSoft px-4 py-3 text-sm text-[#ffe3cf]">
            Following is active. This board is weighting the players and teams you track.
          </div>
        ) : null}

        {feedContext?.personalization_reason ? (
          <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3 text-sm text-muted">
            {feedContext.personalization_reason}
          </div>
        ) : null}

        {!hasActiveFilters && <TrendingSection onOpenDetail={(id) => setDetailSignalId(id)} />}

        {topSignals.length > 0 ? (
          <section className="panel-surface px-4 py-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <div className="eyebrow">Top Signal</div>
                <p className="mt-1 text-sm text-muted">Start here, then scan the rest of the board.</p>
              </div>
              <div className="text-[10px] uppercase tracking-[0.18em] text-muted">{formatRelativeTime(topSignals[0].created_at)}</div>
            </div>
            <button
              type="button"
              onClick={() => setDetailSignalId(topSignals[0].id)}
              className="w-full rounded-[24px] border border-borderStrong bg-white/[0.04] px-4 py-4 text-left transition hover:border-accent/40 hover:bg-white/[0.06]"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-[20px] font-semibold text-ink">{topSignals[0].player_name}</div>
                  <div className="mt-1 text-[15px] leading-6 text-[#e9e2d6]">{topSignals[0].narrative_summary}</div>
                  <div className="mt-2 text-sm text-muted">{topSignals[0].team_name} • {topSignals[0].league_name}</div>
                </div>
                <div className={`shrink-0 text-right text-[24px] font-semibold ${getSignalDirection(topSignals[0]) === 'positive' ? 'text-success' : getSignalDirection(topSignals[0]) === 'negative' ? 'text-danger' : 'text-ink'}`}>
                  {formatDelta(topSignals[0])}
                </div>
              </div>
            </button>
          </section>
        ) : null}

        <div className="min-h-[calc(100vh-22rem)]">
          {loadingInitial ? (
            <LoadingState />
          ) : (
            <SignalFeed
              signals={feedSignals}
              paginated
              feedContext={feedContext}
              onOpenDetail={(id) => setDetailSignalId(id)}
            />
          )}
        </div>

        {currentUser && ingestStatus?.recent_runs?.length ? (
          <section className="panel-surface px-4 py-4">
            <div className="eyebrow mb-3">Ingest History</div>
            <div className="space-y-2">
              {ingestStatus.recent_runs.slice(0, 5).map((run) => (
                <div key={run.started_at} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-white/[0.02] px-3 py-3 text-sm">
                  <div>
                    <div className="text-ink">{new Date(run.started_at).toLocaleString()}</div>
                    <div className="text-xs text-muted">
                      {run.status} · {run.duration_seconds ? `${Math.round(run.duration_seconds)}s` : 'in progress'}
                    </div>
                  </div>
                  {run.error_message ? <div className="max-w-[280px] text-xs text-danger">{run.error_message}</div> : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}
      </div>

      {detailSignalId != null && (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      )}
    </>
  );
}
