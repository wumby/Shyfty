import { useEffect, useState } from 'react';

import { api } from '../services/api';
import type { Signal } from '../types';
import {
  formatDelta,
  formatSignalLabel,
  getImportance,
  getSignalDirection,
} from '../lib/signalFormat';

const typeTone: Record<Signal['signal_type'], string> = {
  SPIKE: 'text-green-400',
  DROP: 'text-red-400',
  SHIFT: 'text-amber-400',
  CONSISTENCY: 'text-blue-400',
  OUTLIER: 'text-purple-400',
};

interface Props {
  onOpenDetail: (id: number) => void;
}

export function TrendingSection({ onOpenDetail }: Props) {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .getTrendingSignals(12)
      .then(setSignals)
      .catch(() => setSignals([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="panel-surface space-y-3 px-4 py-3.5">
        <div className="eyebrow">Trending</div>
        <div className="flex gap-2 overflow-x-auto pb-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-[84px] w-56 flex-none animate-pulse rounded-[20px] bg-white/[0.04]" />
          ))}
        </div>
      </div>
    );
  }

  if (signals.length === 0) return null;

  return (
    <section className="panel-surface px-4 py-3.5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <div className="eyebrow">Trending</div>
          <div className="mt-1 text-sm text-muted">A quick read on the strongest short-term movement.</div>
        </div>
        <div className="hidden text-[11px] uppercase tracking-[0.24em] text-[#ffd8bd] sm:block">Highlights</div>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
        {signals.map((signal) => {
          const direction = getSignalDirection(signal);
          const importance = getImportance(signal);
          const toneClass = typeTone[signal.signal_type];

          return (
            <button
              key={signal.id}
              type="button"
              onClick={() => onOpenDetail(signal.id)}
              className="group flex w-56 flex-none flex-col justify-between rounded-[20px] border border-border bg-white/[0.03] px-3.5 py-3 text-left transition hover:-translate-y-0.5 hover:border-borderStrong hover:bg-white/[0.05]"
            >
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-semibold uppercase tracking-[0.14em] ${toneClass}`}>
                  {formatSignalLabel(signal.signal_type)}
                </span>
                {importance === 'High' && (
                  <span className="accent-dot h-1.5 w-1.5" />
                )}
              </div>
              <div className="mt-1.5">
                <div className="truncate text-[17px] font-semibold text-ink">{signal.player_name}</div>
                <div className="mt-0.5 flex items-center gap-2 text-[11px] text-muted">
                  <span className="uppercase tracking-[0.16em]">{signal.metric_label ?? signal.metric_name.replace(/_/g, ' ')}</span>
                  <span className="text-white/10">•</span>
                  <span>{signal.team_name}</span>
                </div>
              </div>
              <div className={`mt-3 text-[22px] font-semibold tabular-nums leading-none ${
                direction === 'positive' ? 'text-success' : direction === 'negative' ? 'text-danger' : 'text-ink'
              }`}>
                {formatDelta(signal)}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
