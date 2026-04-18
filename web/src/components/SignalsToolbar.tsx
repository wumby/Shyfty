import { useEffect } from 'react';

import type { SignalFilters } from '../types';
import { FilterBar } from './FilterBar';

interface SignalsToolbarProps {
  filters: SignalFilters;
  signalCount: number;
  hasMore: boolean;
  filtersOpen: boolean;
  onOpenFilters: () => void;
  onCloseFilters: () => void;
  onChangeFilters: (filters: SignalFilters) => void;
}

function formatLabel(value: string | undefined, fallback: string) {
  if (!value) return fallback;
  return value.toLowerCase().replace(/_/g, ' ');
}

export function SignalsToolbar({
  filters,
  signalCount,
  hasMore,
  filtersOpen,
  onOpenFilters,
  onCloseFilters,
  onChangeFilters,
}: SignalsToolbarProps) {
  const activeCount = Number(Boolean(filters.league)) + Number(Boolean(filters.signal_type));

  useEffect(() => {
    if (!filtersOpen) return undefined;

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onCloseFilters();
      }
    }

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [filtersOpen, onCloseFilters]);

  return (
    <>
      <section className="panel-surface px-3.5 py-3 sm:px-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={onOpenFilters}
              className={`pill-button ${filtersOpen || activeCount > 0 ? 'pill-button-active' : ''}`}
            >
              Filters
              {activeCount > 0 ? <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px]">{activeCount}</span> : null}
            </button>
            <span className="pill-button">
              League
              <span className="text-ink">{formatLabel(filters.league, 'All')}</span>
            </span>
            <span className="pill-button">
              Type
              <span className="text-ink">{formatLabel(filters.signal_type, 'All')}</span>
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-muted">
            <span>{signalCount}{hasMore ? '+' : ''} live</span>
            {activeCount > 0 ? (
              <button
                type="button"
                onClick={() => onChangeFilters({})}
                className="rounded-full border border-border bg-white/[0.03] px-3 py-2 font-semibold text-muted transition hover:border-borderStrong hover:text-ink"
              >
                Reset
              </button>
            ) : null}
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
          {/* Filters now live in a dedicated drawer so navigation and browsing controls are separate concerns. */}
          <div className="panel-strong absolute inset-y-3 right-3 w-[min(360px,calc(100vw-1.5rem))] overflow-y-auto p-4 sm:right-4 sm:w-[360px]">
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <div className="eyebrow text-[#ffd8bd]">Filters</div>
                <p className="mt-1 text-sm text-muted">
                  Narrow the board without keeping every control pinned to the page.
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
            <FilterBar filters={filters} onChange={onChangeFilters} compact />
          </div>
        </div>
      ) : null}
    </>
  );
}
