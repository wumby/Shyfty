import { useEffect, useState } from 'react';

import { LoadingState } from '../components/LoadingState';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { SignalFeed } from '../components/SignalFeed';
import { SignalsPageHeader } from '../components/SignalsPageHeader';
import { SignalsToolbar } from '../components/SignalsToolbar';
import { TrendingSection } from '../components/TrendingSection';
import { useSignalStore } from '../store/useSignalStore';

export function SignalFeedPage() {
  const { filters, signals, loadingInitial, hasMore, setFilters, fetchSignals } = useSignalStore();
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(false);

  useEffect(() => {
    void fetchSignals();
  }, [fetchSignals, filters]);

  const leagueLabel = filters.league ?? 'All leagues';
  const typeLabel = filters.signal_type ?? 'All signals';
  const countLabel = `${signals.length}${hasMore ? '+' : ''} signals`;

  return (
    <>
      <div className="flex min-w-0 flex-col gap-3">
        <SignalsPageHeader
          leagueLabel={leagueLabel}
          typeLabel={typeLabel}
          countLabel={countLabel}
        />

        <SignalsToolbar
          filters={filters}
          signalCount={signals.length}
          hasMore={hasMore}
          filtersOpen={filtersOpen}
          onOpenFilters={() => setFiltersOpen(true)}
          onCloseFilters={() => setFiltersOpen(false)}
          onChangeFilters={(nextFilters) => setFilters(nextFilters)}
        />

        {!filters.league && !filters.signal_type && (
          <TrendingSection onOpenDetail={(id) => setDetailSignalId(id)} />
        )}

        <div className="min-h-[calc(100vh-22rem)]">
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
    </>
  );
}
