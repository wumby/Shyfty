import type { SignalFilters } from '../types';
import { ActiveFilterChips } from './ActiveFilterChips';

type FeedTab = 'forYou' | 'following';

interface FeedToolbarProps {
  filters: SignalFilters;
  filtersOpen: boolean;
  onOpenFilters: () => void;
  onRemoveFilter: (key: 'league' | 'signal_type' | 'sort') => void;
  activeTab: FeedTab;
  onTabChange: (tab: FeedTab) => void;
}

export function FeedToolbar({ filters, filtersOpen, onOpenFilters, onRemoveFilter, activeTab, onTabChange }: FeedToolbarProps) {
  const hasActiveFilters = !!(filters.league || filters.signal_type || (filters.sort && filters.sort !== 'newest'));

  return (
    <div>
      <div className="flex h-[52px] items-center justify-center gap-3">
        <div className="flex rounded-full border border-border/40 bg-white/[0.04] p-0.5">
          <button
            type="button"
            onClick={() => onTabChange('forYou')}
            className={`rounded-full px-4 py-1.5 text-[13px] font-semibold transition ${
              activeTab === 'forYou' ? 'bg-white/[0.09] text-ink shadow-sm' : 'text-muted hover:text-ink/70'
            }`}
          >
            For You
          </button>
          <button
            type="button"
            onClick={() => onTabChange('following')}
            className={`rounded-full px-4 py-1.5 text-[13px] font-semibold transition ${
              activeTab === 'following' ? 'bg-white/[0.09] text-ink shadow-sm' : 'text-muted hover:text-ink/70'
            }`}
          >
            Following
          </button>
        </div>

        {activeTab === 'forYou' && !filtersOpen ? (
          <button
            type="button"
            onClick={onOpenFilters}
            aria-label="Filters"
            className={`relative flex h-8 w-8 items-center justify-center rounded-full border transition ${
              hasActiveFilters
                ? 'border-accent/40 bg-accentSoft text-[#ffd8bd] hover:border-accent/60'
                : 'border-border bg-white/[0.03] text-muted hover:border-borderStrong hover:text-ink'
            }`}
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />
            </svg>
            {hasActiveFilters && (
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-accent" />
            )}
          </button>
        ) : null}
      </div>

      {activeTab === 'forYou' && hasActiveFilters ? (
        <div className="pb-2">
          <ActiveFilterChips filters={filters} onRemove={onRemoveFilter} />
        </div>
      ) : null}
    </div>
  );
}
