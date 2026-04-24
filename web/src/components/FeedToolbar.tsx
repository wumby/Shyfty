import type { SignalFilters } from '../types';
import { ActiveFilterChips } from './ActiveFilterChips';
import type { ReactNode } from 'react';

interface FeedToolbarProps {
  filters: SignalFilters;
  filtersOpen: boolean;
  onOpenFilters: () => void;
  onRemoveFilter: (key: 'league' | 'signal_type' | 'sort') => void;
  aside?: ReactNode;
}

export function FeedToolbar({ filters, filtersOpen, onOpenFilters, onRemoveFilter, aside }: FeedToolbarProps) {
  return (
    <section className="panel-surface px-5 py-5 sm:px-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold leading-tight text-ink sm:text-4xl">Last Game Signals</h1>
          {aside}
        </div>
        <p className="mt-1.5 max-w-2xl text-sm text-muted">
          Standout performances from the most recent games.
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {!filtersOpen ? (
            <button
              type="button"
              onClick={onOpenFilters}
              className="inline-flex h-8 items-center justify-center rounded-full border border-accent/35 bg-accentSoft px-3 text-xs font-bold text-[#ffd8bd] transition hover:border-accent/60 hover:bg-accent/20"
            >
              Filters
            </button>
          ) : null}
          <ActiveFilterChips filters={filters} onRemove={onRemoveFilter} />
        </div>
      </div>
    </section>
  );
}
