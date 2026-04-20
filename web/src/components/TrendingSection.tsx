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
  const [collapsed, setCollapsed] = useState(true);

  useEffect(() => {
    api
      .getTrendingSignals(12)
      .then(setSignals)
      .catch(() => setSignals([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="panel-surface px-4 py-3">
        <div className="eyebrow">Trending</div>
        <div className="mt-2 flex gap-2 overflow-x-auto pb-1">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-[60px] w-36 flex-none animate-pulse rounded-[16px] bg-white/[0.04]" />
          ))}
        </div>
      </div>
    );
  }

  if (signals.length === 0) return null;

  return (
    <section className="panel-surface px-4 py-2.5">
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="flex items-center gap-2 transition-opacity hover:opacity-80"
        >
          <div className="eyebrow">Trending</div>
          <span className={`text-[9px] text-muted/40 transition-transform duration-200 ${collapsed ? '' : 'rotate-180'}`}>▲</span>
        </button>
        <div className="hidden text-[10px] uppercase tracking-[0.24em] text-[#ffd8bd]/60 sm:block">Pulse</div>
      </div>

      <div className={`card-expand ${collapsed ? '' : 'open'}`}>
        <div>
          <div className="mt-2 flex gap-2 overflow-x-auto pb-1 scrollbar-none">
            {signals.slice(0, 6).map((signal) => {
              const direction = getSignalDirection(signal);
              const importance = getImportance(signal);
              const toneClass = typeTone[signal.signal_type];

              return (
                <button
                  key={signal.id}
                  type="button"
                  onClick={() => onOpenDetail(signal.id)}
                  className="group flex w-36 flex-none flex-col justify-between rounded-[16px] border border-border bg-white/[0.03] px-3 py-2 text-left transition hover:-translate-y-0.5 hover:border-borderStrong hover:bg-white/[0.05]"
                >
                  <div className="flex items-center justify-between">
                    <span className={`text-[10px] font-semibold uppercase tracking-[0.14em] ${toneClass}`}>
                      {formatSignalLabel(signal.signal_type)}
                    </span>
                    {importance === 'High' && <span className="accent-dot h-1.5 w-1.5" />}
                  </div>
                  <div className="mt-1">
                    <div className="truncate text-[13px] font-semibold text-ink">{signal.player_name}</div>
                    <div className="mt-0.5 truncate text-[10px] uppercase tracking-[0.14em] text-muted">{signal.team_name}</div>
                  </div>
                  <div className={`mt-1.5 text-[16px] font-semibold tabular-nums leading-none ${
                    direction === 'positive' ? 'text-success' : direction === 'negative' ? 'text-danger' : 'text-ink'
                  }`}>
                    {formatDelta(signal)}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
