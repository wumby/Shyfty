import { useEffect, useRef, useState } from 'react';

import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
import { SearchInput } from '../components/SearchInput';
import { SectionHeader } from '../components/SectionHeader';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { SignalFeed } from '../components/SignalFeed';
import { api } from '../services/api';
import { useSignalStore } from '../store/useSignalStore';
import type { PaginatedSignals, SignalType, SortMode } from '../types';

const SIGNAL_TYPES: SignalType[] = ['SPIKE', 'DROP', 'SHIFT', 'OUTLIER'];
const LEAGUES = ['NBA', 'NFL'];
const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'newest', label: 'Newest' },
  { value: 'most_important', label: 'Most Important' },
  { value: 'biggest_deviation', label: 'Biggest Change' },
  { value: 'most_discussed', label: 'Most Discussed' },
];

function defaultDateFrom(): string {
  const d = new Date();
  d.setDate(d.getDate() - 30);
  return d.toISOString().split('T')[0];
}

function defaultDateTo(): string {
  return new Date().toISOString().split('T')[0];
}

export function ExplorePage() {
  const { players, fetchPlayers } = useSignalStore();
  const [dateFrom, setDateFrom] = useState(defaultDateFrom);
  const [dateTo, setDateTo] = useState(defaultDateTo);
  const [league, setLeague] = useState('');
  const [signalType, setSignalType] = useState('');
  const [player, setPlayer] = useState('');
  const [sort, setSort] = useState<SortMode>('newest');
  const [page, setPage] = useState<PaginatedSignals | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const playerDebounce = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [debouncedPlayer, setDebouncedPlayer] = useState('');

  useEffect(() => {
    if (players.length === 0) void fetchPlayers();
  }, [fetchPlayers, players.length]);

  useEffect(() => {
    if (playerDebounce.current) clearTimeout(playerDebounce.current);
    playerDebounce.current = setTimeout(() => setDebouncedPlayer(player), 300);
    return () => {
      if (playerDebounce.current) clearTimeout(playerDebounce.current);
    };
  }, [player]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const result = await api.getSignals({
          league: league || undefined,
          signal_type: signalType || undefined,
          player: debouncedPlayer || undefined,
          sort,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        });
        setPage(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Query failed');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [dateFrom, dateTo, league, signalType, debouncedPlayer, sort]);

  async function loadMore() {
    if (!page?.has_more || !page.next_cursor) return;
    try {
      const next = await api.getSignals(
        {
          league: league || undefined,
          signal_type: signalType || undefined,
          player: debouncedPlayer || undefined,
          sort,
          date_from: dateFrom || undefined,
          date_to: dateTo || undefined,
        },
        page.next_cursor,
      );
      setPage((prev) => (prev ? { ...next, items: [...prev.items, ...next.items] } : next));
    } catch {
      // ignore load-more failures
    }
  }

  function resetFilters() {
    setDateFrom(defaultDateFrom());
    setDateTo(defaultDateTo());
    setLeague('');
    setSignalType('');
    setPlayer('');
    setSort('newest');
  }

  const count = page?.items.length ?? 0;
  const leagueLabel = league || 'all leagues';
  const rangeLabel = dateFrom === dateTo ? dateFrom : `${dateFrom} to ${dateTo}`;
  const resultsSummary = `Showing ${count}${page?.has_more ? '+' : ''} signals for ${leagueLabel}, ${rangeLabel}`;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-4">
        <PageIntro
          eyebrow="Search Tool"
          title="Explore"
          description="Search and filter historical signals. Start with a player, league, or signal type, then review the results summary before opening a signal."
        />

        <div className="grid gap-4 lg:grid-cols-[320px,minmax(0,1fr)]">
          <aside className="panel-surface px-4 py-4">
            <SectionHeader
              title="Filters"
              description="Refine the search first, then read the results on the right."
              aside={
                <button
                  type="button"
                  onClick={resetFilters}
                  className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted transition hover:border-borderStrong hover:text-ink"
                >
                  Reset
                </button>
              }
            />

            <div className="mt-4 space-y-4">
              <div>
                <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Player</label>
                <SearchInput
                  value={player}
                  players={players}
                  onChange={setPlayer}
                  placeholder="Search by player"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">From</label>
                  <input
                    type="date"
                    value={dateFrom}
                    max={dateTo || undefined}
                    onChange={(e) => setDateFrom(e.target.value)}
                    className="field-shell w-full px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">To</label>
                  <input
                    type="date"
                    value={dateTo}
                    min={dateFrom || undefined}
                    onChange={(e) => setDateTo(e.target.value)}
                    className="field-shell w-full px-3 py-2 text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">League</label>
                <select
                  value={league}
                  onChange={(e) => setLeague(e.target.value)}
                  className="field-shell w-full px-3 py-2 text-sm"
                >
                  <option value="">All leagues</option>
                  {LEAGUES.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Signal type</label>
                <select
                  value={signalType}
                  onChange={(e) => setSignalType(e.target.value)}
                  className="field-shell w-full px-3 py-2 text-sm"
                >
                  <option value="">All signal types</option>
                  {SIGNAL_TYPES.map((item) => (
                    <option key={item} value={item}>{item}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-2 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Sort</label>
                <select
                  value={sort}
                  onChange={(e) => setSort(e.target.value as SortMode)}
                  className="field-shell w-full px-3 py-2 text-sm"
                >
                  {SORT_OPTIONS.map((item) => (
                    <option key={item.value} value={item.value}>{item.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </aside>

          <section className="panel-surface px-4 py-4">
            <SectionHeader
              title="Results"
              description="Open a signal to understand the cause, then adjust the filters if the list is too broad or too narrow."
              aside={<div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">{resultsSummary}</div>}
            />

            <div className="mt-4 rounded-[18px] bg-white/[0.03] px-3 py-2 text-sm text-muted">
              {resultsSummary}
            </div>

            <div className="mt-4 min-h-[480px]">
              {error ? (
                <div className="rounded-[22px] border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-[#f2c1c1]">{error}</div>
              ) : loading ? (
                <LoadingState />
              ) : page && page.items.length === 0 ? (
                <div className="rounded-[22px] bg-white/[0.02] px-4 py-8 text-center text-sm text-muted">
                  No signals match these filters. Broaden the date range or remove a filter to keep exploring.
                </div>
              ) : page ? (
                <div className="space-y-4">
                  <SignalFeed signals={page.items} onOpenDetail={(id) => setDetailSignalId(id)} />
                  {page.has_more ? (
                    <button
                      type="button"
                      onClick={() => void loadMore()}
                      className="mx-auto block rounded-full border border-border bg-white/[0.03] px-5 py-2.5 text-sm font-semibold text-muted transition hover:border-borderStrong hover:text-ink"
                    >
                      Load more results
                    </button>
                  ) : null}
                </div>
              ) : null}
            </div>
          </section>
        </div>
      </div>

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </>
  );
}
