import { useEffect } from 'react';

import type { FeedMode, Player, SignalFilters, SortMode } from '../types';
import { FilterBar } from './FilterBar';
import { SearchInput } from './SearchInput';

interface SignalsToolbarProps {
  filters: SignalFilters;
  players: Player[];
  signalCount: number;
  hasMore: boolean;
  filtersOpen: boolean;
  onOpenFilters: () => void;
  onCloseFilters: () => void;
  onChangeFilters: (filters: SignalFilters) => void;
}

const sortOptions: Array<{ value: SortMode; label: string }> = [
  { value: 'newest', label: 'Newest' },
  { value: 'most_discussed', label: 'Most Discussed' },
  { value: 'most_important', label: 'Most Important' },
  { value: 'biggest_deviation', label: 'Biggest Deviation' },
];

const feedOptions: Array<{ value: FeedMode; label: string }> = [
  { value: 'all', label: 'All' },
  { value: 'following', label: 'Following' },
  { value: 'for_you', label: 'For You' },
];

function formatLabel(value: string | undefined, fallback: string) {
  if (!value) return fallback;
  return value.toLowerCase().replace(/_/g, ' ');
}

export function SignalsToolbar({
  filters,
  players,
  signalCount,
  hasMore,
  filtersOpen,
  onOpenFilters,
  onCloseFilters,
  onChangeFilters,
}: SignalsToolbarProps) {
  const activeCount =
    Number(Boolean(filters.league)) +
    Number(Boolean(filters.signal_type)) +
    Number(Boolean(filters.player));

  useEffect(() => {
    if (!filtersOpen) return undefined;
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') onCloseFilters();
    }
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [filtersOpen, onCloseFilters]);

  return (
    <>
      <section className="panel-surface px-3.5 py-3 sm:px-4">
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex flex-1 flex-wrap items-center gap-2">
              <div className="w-full max-w-[240px] sm:max-w-[280px]">
                <SearchInput
                  value={filters.player ?? ''}
                  players={players}
                  onChange={(val) => onChangeFilters({ ...filters, player: val || undefined })}
                  placeholder="Search players…"
                />
              </div>

              <button
                type="button"
                onClick={onOpenFilters}
                className={`pill-button ${filtersOpen || activeCount > (filters.player ? 1 : 0) ? 'pill-button-active' : ''}`}
              >
                Filters
                {activeCount > 0 ? <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px]">{activeCount}</span> : null}
              </button>

              {filters.league && (
                <span className="pill-button">
                  League <span className="text-ink">{formatLabel(filters.league, 'All')}</span>
                </span>
              )}
              {filters.signal_type && (
                <span className="pill-button">
                  Type <span className="text-ink">{formatLabel(filters.signal_type, 'All')}</span>
                </span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted">
              <span>{signalCount}{hasMore ? '+' : ''} live</span>
              {activeCount > 0 ? (
                <button
                  type="button"
                  onClick={() => onChangeFilters({ sort: filters.sort ?? 'newest', feed: filters.feed ?? 'all' })}
                  className="rounded-full border border-border bg-white/[0.03] px-3 py-2 font-semibold text-muted transition hover:border-borderStrong hover:text-ink"
                >
                  Reset
                </button>
              ) : null}
            </div>
          </div>

          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex flex-wrap gap-2">
              {feedOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChangeFilters({ ...filters, feed: option.value })}
                  className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                    (filters.feed ?? 'all') === option.value
                      ? option.value === 'following'
                        ? 'border-accent/50 bg-accentSoft text-[#fff0e1] shadow-[0_0_22px_rgba(249,115,22,0.16)]'
                        : 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                      : 'border-border bg-white/[0.03] text-muted hover:border-borderStrong hover:text-ink'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {sortOptions.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => onChangeFilters({ ...filters, sort: option.value })}
                  className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                    (filters.sort ?? 'newest') === option.value
                      ? option.value === 'most_discussed'
                        ? 'border-accent/50 bg-accentSoft text-[#fff0e1] shadow-[0_0_22px_rgba(249,115,22,0.14)]'
                        : 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                      : option.value === 'most_discussed'
                        ? 'border-accent/20 bg-accent/5 text-[#f4c39f] hover:border-accent/40 hover:text-[#ffe2cb]'
                      : 'border-border bg-white/[0.03] text-muted hover:border-borderStrong hover:text-ink'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {filtersOpen ? (
        <div className="fixed inset-0 z-40">
          <button
            type="button"
            aria-label="Close filters"
            onClick={onCloseFilters}
            className="absolute inset-0 bg-[#02060d]/70 backdrop-blur-sm"
          />
          <div className="panel-strong absolute inset-y-3 right-3 w-[min(360px,calc(100vw-1.5rem))] overflow-y-auto p-4 sm:right-4 sm:w-[360px]">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <div className="eyebrow text-[#ffd8bd]">Filters</div>
                <p className="mt-1 text-sm text-muted">
                  Narrow the board by league, signal type, or player.
                </p>
              </div>
              <button
                type="button"
                onClick={onCloseFilters}
                className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted transition hover:border-borderStrong hover:text-ink"
              >
                Close
              </button>
            </div>
            <FilterBar filters={filters} players={players} onChange={onChangeFilters} compact />
          </div>
        </div>
      ) : null}
    </>
  );
}
