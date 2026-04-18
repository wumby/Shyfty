import { useEffect, useState } from 'react';

import { FilterBar } from '../components/FilterBar';
import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { SignalFeed } from '../components/SignalFeed';
import { TrendingSection } from '../components/TrendingSection';
import { useSignalStore } from '../store/useSignalStore';

export function SignalFeedPage() {
  const { filters, signals, loadingInitial, hasMore, setFilters, fetchSignals } = useSignalStore();
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals, filters]);

  const leagueLabel = filters.league ?? 'All leagues';
  const typeLabel = filters.signal_type ?? 'All signals';
  const countLabel = `${signals.length}${hasMore ? '+' : ''} signals`;

  return (
    <div className="grid h-[calc(100vh-7.7rem)] gap-3 lg:grid-cols-[220px,minmax(0,1fr)]">
      <aside className="hidden lg:block">
        <div className="sticky top-0">
          <FilterBar
            filters={filters}
            onChange={(nextFilters) => setFilters(nextFilters)}
          />
        </div>
      </aside>

      <div className="flex min-h-0 flex-col overflow-hidden rounded-[28px] border border-border bg-transparent">
        <div className="hero-grid rounded-[28px] border border-border bg-white/[0.03] px-4 py-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="eyebrow">Signal Feed</div>
              <h1 className="mt-2 text-4xl font-semibold text-ink">Read the board, not just the box score.</h1>
            </div>
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] uppercase tracking-[0.2em] text-muted">
            <span>{leagueLabel}</span>
            <span className="text-white/10">/</span>
            <span>{typeLabel}</span>
            <span className="text-white/10">/</span>
            <span>{countLabel}</span>
            </div>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <div className="px-3 pt-3 sm:px-4">
            <div className="lg:hidden pb-3">
              <FilterBar
                filters={filters}
                onChange={(nextFilters) => setFilters(nextFilters)}
              />
            </div>
            {!filters.league && !filters.signal_type && (
              <TrendingSection onOpenDetail={(id) => setDetailSignalId(id)} />
            )}
          </div>
          {loadingInitial ? (
            <LoadingState />
          ) : (
            <SignalFeed
              signals={signals}
              paginated
              onOpenDetail={(id) => setDetailSignalId(id)}
            />
          )}
        </div>
      </div>

      {detailSignalId != null && (
        <SignalDetailDrawer
          signalId={detailSignalId}
          onClose={() => setDetailSignalId(null)}
        />
      )}
    </div>
  );
}
