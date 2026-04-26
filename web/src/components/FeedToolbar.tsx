import type { ReactNode } from 'react';

import type { SignalFilters } from '../types';
import { ActiveFilterChips } from './ActiveFilterChips';

type FeedTab = 'forYou' | 'following';

interface FeedToolbarProps {
  filters: SignalFilters;
  filtersOpen: boolean;
  onOpenFilters: () => void;
  onRemoveFilter: (key: 'league' | 'signal_type' | 'sort') => void;
  aside?: ReactNode;
  activeTab: FeedTab;
  onTabChange: (tab: FeedTab) => void;
}

export function FeedToolbar({ filters, filtersOpen, onOpenFilters, onRemoveFilter, aside, activeTab, onTabChange }: FeedToolbarProps) {
  return (
    <section className="panel-surface px-5 py-5 sm:px-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-bold leading-tight text-ink sm:text-4xl">Signals</h1>
          {aside}
        </div>
        <p className="mt-1.5 max-w-2xl text-sm text-muted">
          Standout performances from recent games.
        </p>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <div className="flex rounded-full border border-border/50 bg-white/[0.03] p-0.5">
            <button
              type="button"
              onClick={() => onTabChange('forYou')}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                activeTab === 'forYou'
                  ? 'bg-white/[0.08] text-ink shadow-sm'
                  : 'text-muted hover:text-ink/70'
              }`}
            >
              For You
            </button>
            <button
              type="button"
              onClick={() => onTabChange('following')}
              className={`rounded-full px-4 py-1.5 text-xs font-semibold transition ${
                activeTab === 'following'
                  ? 'bg-white/[0.08] text-ink shadow-sm'
                  : 'text-muted hover:text-ink/70'
              }`}
            >
              Following
            </button>
          </div>
          {!filtersOpen && activeTab === 'forYou' ? (
            <button
              type="button"
              onClick={onOpenFilters}
              className="inline-flex h-8 items-center justify-center rounded-full border border-accent/35 bg-accentSoft px-3 text-xs font-bold text-[#ffd8bd] transition hover:border-accent/60 hover:bg-accent/20"
            >
              Filters
            </button>
          ) : null}
          {activeTab === 'forYou' ? (
            <ActiveFilterChips filters={filters} onRemove={onRemoveFilter} />
          ) : null}
        </div>
      </div>
    </section>
  );
}
