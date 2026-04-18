import { useEffect, useRef } from 'react';

import { EmptyState } from './EmptyState';
import { SignalCard } from './SignalCard';
import type { Signal } from '../types';
import { useSignalStore } from '../store/useSignalStore';

interface SignalFeedProps {
  signals: Signal[];
  onOpenDetail?: (signalId: number) => void;
  /** When true, wires the sentinel to the global store's loadMore (main feed). */
  paginated?: boolean;
}

export function SignalFeed({ signals, onOpenDetail, paginated = false }: SignalFeedProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadMore = useSignalStore((state) => state.loadMore);
  const hasMore = useSignalStore((state) => state.hasMore);
  const loadingMore = useSignalStore((state) => state.loadingMore);

  useEffect(() => {
    if (!paginated) return undefined;
    const sentinel = sentinelRef.current;
    if (!sentinel) return undefined;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting && hasMore && !loadingMore) {
          void loadMore();
        }
      },
      { root: containerRef.current, rootMargin: '300px 0px' },
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [paginated, hasMore, loadingMore, loadMore]);

  if (!signals.length) {
    return (
      <div className="h-full overflow-y-auto" ref={containerRef}>
        <EmptyState
          title="No signals in this view"
          copy="Try broadening the league or signal type filter. New signals appear when games are ingested."
        />
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto" ref={containerRef}>
      <div className="panel-surface overflow-hidden bg-transparent">
        {signals.map((signal) => (
          <SignalCard key={signal.id} signal={signal} onOpenDetail={onOpenDetail} />
        ))}
        {paginated && hasMore && (
          <div ref={sentinelRef} className="flex items-center justify-center py-4">
            {loadingMore && (
              <div className="text-[11px] uppercase tracking-[0.2em] text-muted">Loading more…</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
