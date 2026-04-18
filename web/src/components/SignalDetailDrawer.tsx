import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

import { api } from '../services/api';
import type { SignalTrace } from '../types';
import { formatEventDate, formatSignalLabel, getMetricLabel } from '../lib/signalFormat';

interface Props {
  signalId: number;
  onClose: () => void;
}

function buildWhatChanged(trace: SignalTrace): string | null {
  const { signal, rolling_metric, baseline_samples } = trace;
  if (!rolling_metric || !signal) return null;

  const metric = signal.metric_label ?? signal.metric_name.replace(/_/g, ' ');
  const current = signal.current_value;
  const baseline = signal.baseline_value;
  const z = rolling_metric.z_score;
  const stddev = rolling_metric.rolling_stddev;

  if (signal.signal_type === 'CONSISTENCY') {
    return `${metric} has been locked in — the last ${baseline_samples.length + 1} games show almost no variance (σ = ${stddev.toFixed(2)}), staying right around ${baseline.toFixed(1)}.`;
  }

  if (signal.signal_type === 'SHIFT') {
    const dir = current > baseline ? 'climbing' : 'dropping';
    return `${metric} role is ${dir}. The z-score of ${z.toFixed(2)} signals a meaningful shift in playing time or usage relative to the recent baseline of ${baseline.toFixed(1)}.`;
  }

  const pct = baseline > 0.05 ? Math.abs(Math.round(((current - baseline) / baseline) * 100)) : null;
  const dir = current >= baseline ? 'above' : 'below';
  const qualifier = Math.abs(z) >= 2.5 ? 'dramatically' : Math.abs(z) >= 1.5 ? 'notably' : '';

  let sentence = `${metric} hit ${current.toFixed(1)} — ${qualifier ? qualifier + ' ' : ''}${dir} the ${baseline_samples.length}-game baseline of ${baseline.toFixed(1)}`;
  if (pct !== null) sentence += ` (${pct}% ${dir})`;
  sentence += `.`;

  if (stddev > 0) {
    sentence += ` The standard deviation over the window is ${stddev.toFixed(2)}, making this a z-score of ${Math.abs(z).toFixed(2)}.`;
  }

  return sentence;
}

const signalTypeColor: Record<string, string> = {
  SPIKE: 'text-emerald-300',
  DROP: 'text-rose-300',
  SHIFT: 'text-amber-300',
  CONSISTENCY: 'text-sky-300',
  OUTLIER: 'text-fuchsia-300',
};

export function SignalDetailDrawer({ signalId, onClose }: Props) {
  const [trace, setTrace] = useState<SignalTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setTrace(null);
    api
      .getSignalTrace(signalId)
      .then(setTrace)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [signalId]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const signal = trace?.signal;
  const whatChanged = trace ? buildWhatChanged(trace) : null;

  return createPortal(
    <>
      <div className="fixed inset-0 z-[70] bg-black/45 backdrop-blur-[6px]" onClick={onClose} />

      <div
        ref={drawerRef}
        className="fixed bottom-3 right-3 top-3 z-[80] flex w-[calc(100%-1.5rem)] max-w-[460px] flex-col overflow-hidden rounded-[28px] border border-borderStrong bg-[#07111f]/95 shadow-2xl backdrop-blur-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="eyebrow">Signal Analysis</div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs text-muted transition hover:text-ink"
          >
            Close ✕
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {loading && (
            <div className="animate-pulse space-y-4">
              <div className="h-6 w-48 rounded bg-white/[0.07]" />
              <div className="h-4 w-full rounded bg-white/[0.04]" />
              <div className="h-4 w-3/4 rounded bg-white/[0.04]" />
              <div className="mt-6 h-20 w-full rounded bg-white/[0.04]" />
              <div className="h-4 w-32 rounded bg-white/[0.07]" />
              <div className="h-32 w-full rounded bg-white/[0.04]" />
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
              {error}
            </div>
          )}

          {trace && signal && (
            <div className="space-y-6">
              <div>
                <div className={`text-xs font-semibold uppercase tracking-[0.2em] ${signalTypeColor[signal.signal_type] ?? 'text-slate-400'}`}>
                  {formatSignalLabel(signal.signal_type as Parameters<typeof formatSignalLabel>[0])} · {signal.league_name}
                </div>
                <h3 className="mt-1 text-3xl font-semibold text-ink">{signal.player_name}</h3>
                <p className="mt-0.5 text-sm text-muted">
                  {signal.team_name} · {getMetricLabel(signal)}
                </p>
                {signal.event_date && (
                  <p className="mt-0.5 text-xs text-muted/70">{formatEventDate(signal.event_date)}</p>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3 rounded-[26px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">This Game</div>
                  <div className={`mt-1 text-2xl font-bold tabular-nums ${
                    signal.trend_direction === 'up' ? 'text-success' :
                    signal.trend_direction === 'down' ? 'text-danger' : 'text-ink'
                  }`}>
                    {signal.current_value.toFixed(1)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Baseline</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-muted">
                    {signal.baseline_value.toFixed(1)}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Z-Score</div>
                  <div className={`mt-1 text-2xl font-bold tabular-nums ${
                    Math.abs(signal.z_score) >= 2.5 ? 'text-fuchsia-300' :
                    Math.abs(signal.z_score) >= 1.5 ? 'text-warning' : 'text-ink'
                  }`}>
                    {signal.z_score > 0 ? '+' : ''}{signal.z_score.toFixed(2)}
                  </div>
                </div>
              </div>

              {whatChanged && (
                <div>
                  <div className="eyebrow mb-2">What This Means</div>
                  <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                    <p className="text-sm leading-relaxed text-[#d9e3f1]">{whatChanged}</p>
                  </div>
                </div>
              )}

              {trace.rolling_metric && (
                <div>
                  <div className="eyebrow mb-2">Why It Triggered</div>
                  <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                    <div className="mb-3 text-[11px] uppercase tracking-[0.14em] text-muted">{signal.classification_reason}</div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-muted">Rolling Avg</div>
                        <div className="mt-0.5 font-mono text-base font-semibold text-ink">
                          {trace.rolling_metric.rolling_avg.toFixed(1)}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted">Std Dev (σ)</div>
                        <div className="mt-0.5 font-mono text-base font-semibold text-ink">
                          {trace.rolling_metric.rolling_stddev.toFixed(2)}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 border-t border-border pt-3 text-xs text-muted">
                      {signal.baseline_window}
                    </div>
                  </div>
                </div>
              )}

              {trace.baseline_samples.length > 0 && (
                <div>
                  <div className="eyebrow mb-2">
                    Recent History — {signal.baseline_window}
                  </div>
                  <div className="overflow-hidden rounded-[22px] border border-border">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border bg-white/[0.03]">
                          <th className="px-3 py-2 text-left text-[10px] uppercase tracking-[0.16em] text-muted">Date</th>
                          <th className="px-3 py-2 text-right text-[10px] uppercase tracking-[0.16em] text-muted">
                            {getMetricLabel(signal)}
                          </th>
                          <th className="px-3 py-2 text-right text-[10px] uppercase tracking-[0.16em] text-muted">vs avg</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trace.baseline_samples.map((sample, i) => {
                          const diff = sample.value - signal.baseline_value;
                          return (
                            <tr
                              key={sample.stat_id}
                              className={`border-b border-border/70 ${i % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.02]'}`}
                            >
                              <td className="px-3 py-2 text-muted">{formatEventDate(sample.game_date)}</td>
                              <td className="px-3 py-2 text-right font-mono font-medium text-[#d9e3f1]">
                                {sample.value.toFixed(1)}
                              </td>
                              <td className={`px-3 py-2 text-right font-mono text-xs ${diff > 0 ? 'text-success/80' : diff < 0 ? 'text-danger/80' : 'text-muted/80'}`}>
                                {diff > 0 ? '+' : ''}{diff.toFixed(1)}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-muted">
                    <span>Baseline avg over this window</span>
                    <span className="font-mono font-medium text-ink">{signal.baseline_value.toFixed(1)}</span>
                  </div>
                </div>
              )}

              {trace.source_stat && (
                <div>
                  <div className="eyebrow mb-2">Full Game Stats</div>
                  <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                    <div className="mb-3 text-xs text-muted">{formatEventDate(trace.source_stat.game_date)}</div>
                    <div className="flex items-center justify-between border-b border-border pb-3">
                      <span className="text-sm font-medium text-[#d9e3f1]">{getMetricLabel(signal)}</span>
                      <span className={`font-mono text-xl font-bold ${
                        signal.trend_direction === 'up' ? 'text-success' :
                        signal.trend_direction === 'down' ? 'text-danger' : 'text-ink'
                      }`}>
                        {trace.source_stat.current_value.toFixed(1)}
                      </span>
                    </div>
                    {Object.keys(trace.source_stat.raw_stats).length > 1 && (
                      <div className="mt-3 grid grid-cols-3 gap-3">
                        {Object.entries(trace.source_stat.raw_stats)
                          .filter(([k]) => k !== signal.metric_name)
                          .slice(0, 9)
                          .map(([key, val]) => (
                            <div key={key} className="text-center">
                              <div className="text-[10px] uppercase tracking-[0.1em] text-muted/80">
                                {key.replace(/_/g, ' ')}
                              </div>
                              <div className="mt-0.5 font-mono text-sm font-medium text-muted">
                                {typeof val === 'number' ? val.toFixed(1) : val}
                              </div>
                            </div>
                          ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </>,
    document.body
  );
}
