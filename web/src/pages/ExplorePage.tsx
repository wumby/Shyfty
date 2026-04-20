import { useEffect, useRef, useState } from 'react';

import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { SignalFeed } from '../components/SignalFeed';
import { api } from '../services/api';
import type { PaginatedSignals, SignalType, SortMode } from '../types';

const SIGNAL_TYPES: SignalType[] = ['SPIKE', 'DROP', 'SHIFT', 'CONSISTENCY', 'OUTLIER'];
const LEAGUES = ['NBA', 'NFL'];
const SORT_OPTIONS: { value: SortMode; label: string }[] = [
  { value: 'newest', label: 'Newest' },
  { value: 'most_important', label: 'Most Important' },
  { value: 'biggest_deviation', label: 'Biggest Deviation' },
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
    if (playerDebounce.current) clearTimeout(playerDebounce.current);
    playerDebounce.current = setTimeout(() => setDebouncedPlayer(player), 350);
    return () => { if (playerDebounce.current) clearTimeout(playerDebounce.current); };
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
      setPage((prev) => prev
        ? { ...next, items: [...prev.items, ...next.items] }
        : next
      );
    } catch {
      // ignore load more errors
    }
  }

  const count = page?.items.length ?? 0;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-5">
        <div>
          <div className="flex items-baseline justify-between gap-3">
            <div>
              <h1 className="text-[26px] font-semibold text-ink">Explore</h1>
              <p className="mt-1 text-sm text-muted">Search historical signals from the Shyfty DB — no upstream calls.</p>
            </div>
            {count > 0 && (
              <div className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                {count}{page?.has_more ? '+' : ''} results
              </div>
            )}
          </div>
        </div>

        <section className="panel-surface px-4 py-4">
          <div className="eyebrow mb-3">Filters</div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">From</label>
              <input
                type="date"
                value={dateFrom}
                max={dateTo || undefined}
                onChange={(e) => setDateFrom(e.target.value)}
                className="rounded-[14px] border border-border bg-white/[0.03] px-3 py-2 text-sm text-ink focus:border-accent/50 focus:outline-none"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">To</label>
              <input
                type="date"
                value={dateTo}
                min={dateFrom || undefined}
                onChange={(e) => setDateTo(e.target.value)}
                className="rounded-[14px] border border-border bg-white/[0.03] px-3 py-2 text-sm text-ink focus:border-accent/50 focus:outline-none"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">Player</label>
              <input
                type="text"
                placeholder="Any player"
                value={player}
                onChange={(e) => setPlayer(e.target.value)}
                className="rounded-[14px] border border-border bg-white/[0.03] px-3 py-2 text-sm text-ink placeholder:text-muted/50 focus:border-accent/50 focus:outline-none"
              />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">League</label>
              <select
                value={league}
                onChange={(e) => setLeague(e.target.value)}
                className="rounded-[14px] border border-border bg-[#1a1410] px-3 py-2 text-sm text-ink focus:border-accent/50 focus:outline-none"
              >
                <option value="">All leagues</option>
                {LEAGUES.map((l) => <option key={l} value={l}>{l}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">Signal Type</label>
              <select
                value={signalType}
                onChange={(e) => setSignalType(e.target.value)}
                className="rounded-[14px] border border-border bg-[#1a1410] px-3 py-2 text-sm text-ink focus:border-accent/50 focus:outline-none"
              >
                <option value="">All types</option>
                {SIGNAL_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-[10px] uppercase tracking-[0.14em] text-muted">Sort</label>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortMode)}
                className="rounded-[14px] border border-border bg-[#1a1410] px-3 py-2 text-sm text-ink focus:border-accent/50 focus:outline-none"
              >
                {SORT_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
          </div>
        </section>

        {error ? (
          <div className="rounded-[22px] border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-[#f2c1c1]">{error}</div>
        ) : loading ? (
          <LoadingState />
        ) : page && page.items.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted">No signals found for these filters.</div>
        ) : page ? (
          <>
            <SignalFeed signals={page.items} onOpenDetail={(id) => setDetailSignalId(id)} />
            {page.has_more && (
              <button
                type="button"
                onClick={() => void loadMore()}
                className="mx-auto rounded-full border border-border bg-white/[0.03] px-5 py-2.5 text-sm font-semibold text-muted transition hover:border-borderStrong hover:text-ink"
              >
                Load more
              </button>
            )}
          </>
        ) : null}
      </div>

      {detailSignalId != null && (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      )}
    </>
  );
}
