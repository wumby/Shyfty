import { useEffect, useRef } from 'react';

import { EmptyState } from './EmptyState';
import { SignalCard } from './SignalCard';
import type { FeedContext, Signal } from '../types';
import { useSignalStore } from '../store/useSignalStore';
import { getSignalMomentum } from '../lib/signalFormat';

interface SignalFeedProps {
  signals: Signal[];
  onOpenDetail?: (signalId: number) => void;
  /** When true, wires the sentinel to the global store's loadMore (main feed). */
  paginated?: boolean;
  feedContext?: FeedContext | null;
}

export function SignalFeed({ signals, onOpenDetail, paginated = false, feedContext = null }: SignalFeedProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadMore = useSignalStore((state) => state.loadMore);
  const hasMore = useSignalStore((state) => state.hasMore);
  const loadingMore = useSignalStore((state) => state.loadingMore);
  const profile = useSignalStore((state) => state.profile);

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
          title={feedContext?.feed_mode === 'following' ? 'Nothing in following yet' : feedContext?.feed_mode === 'for_you' ? 'Your board needs a little history' : 'No signals in this view'}
          copy={feedContext?.personalization_reason ?? 'Try broadening the league or signal type filter. New signals appear when games are ingested.'}
        />
      </div>
    );
  }

  const rankedSignals = [...signals]
    .map((signal, index) => {
      const isTracked =
        (signal.player_id != null && profile?.follows.players.includes(signal.player_id)) ||
        profile?.follows.teams.includes(signal.team_id) ||
        false;
      const momentum = getSignalMomentum(signal, isTracked, feedContext?.sort_mode);

      return {
        signal,
        index,
        featuredScore: momentum,
        softRank: -index + momentum * 0.45,
      };
    })
    .sort((left, right) => right.softRank - left.softRank);

  const featuredIds = new Set(
    [...rankedSignals]
      .sort((left, right) => right.featuredScore - left.featuredScore)
      .slice(0, 2)
      .map(({ signal }) => signal.id),
  );

  return (
    <div className="h-full overflow-y-auto" ref={containerRef}>
      <div className="panel-surface overflow-hidden bg-transparent">
        {rankedSignals.map(({ signal }) => (
          <SignalCard key={signal.id} signal={signal} onOpenDetail={onOpenDetail} />
        ))}
        {paginated && hasMore && (
          <div ref={sentinelRef} className="flex items-center justify-center px-4 py-4">
            {loadingMore && (
              <div className="text-[11px] uppercase tracking-[0.2em] text-muted">Loading more…</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
