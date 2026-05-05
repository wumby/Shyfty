import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import type { ShyftTrace } from '../types';
import { formatEventDate, formatShyftLabel, getMetricLabel } from "../lib/shyftFormat";
import { useShyftStore } from "../store/useShyftStore";

interface Props {
  shyftId: number;
  onClose: () => void;
}

const shyftTypeColor: Record<string, string> = {
  OUTLIER: 'text-red-300',
  SWING: 'text-amber-300',
  SHIFT: 'text-white/50',
};

function formatNumber(value: number): string {
  return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1);
}

function formatSigned(value: number): string {
  return `${value >= 0 ? '+' : ''}${formatNumber(value)}`;
}

function formatThresholdValue(value: number | null): string {
  if (value === null) return 'not used';
  return Number.isInteger(value) ? value.toFixed(0) : value.toFixed(2).replace(/0+$/, '').replace(/\.$/, '');
}

const gateLabels: Record<string, string> = {
  sample_size: 'Sample size',
  baseline_or_actual: 'Baseline or actual',
  baseline: 'Baseline',
  actual: 'Actual',
  delta: 'Delta',
  z_score: 'Z-score',
  minutes_guard: 'Minutes guard',
};

export function ShyftDetailDrawer({ shyftId, onClose }: Props) {
  const [trace, setTrace] = useState<ShyftTrace | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const mergeShyftMeta = useShyftStore((s) => s.mergeShyftMeta);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    setError(null);
    setTrace(null);
    api
      .getShyft(shyftId)
      .then((loadedTrace) => {
        setTrace(loadedTrace);
        mergeShyftMeta(loadedTrace.shyft);
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false));
  }, [mergeShyftMeta, shyftId]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  const shyft = trace?.shyft;

  return createPortal(
    <>
      <div className="fixed inset-0 z-[70] bg-black/45 backdrop-blur-[6px]" onClick={onClose} />

      <div
        ref={drawerRef}
        className="fixed bottom-3 right-3 top-3 z-[80] flex w-[calc(100%-1.5rem)] max-w-[520px] flex-col overflow-hidden rounded-[28px] border border-borderStrong bg-[#07111f]/95 shadow-2xl backdrop-blur-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="eyebrow">Shyft Analysis</div>
          <div className="flex items-center gap-3">
            <button type="button" onClick={onClose} className="text-xs text-muted transition hover:text-ink">
              Close ✕
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {loading && <div className="animate-pulse space-y-4"><div className="h-6 w-48 rounded bg-white/[0.07]" /><div className="h-28 rounded bg-white/[0.04]" /><div className="h-48 rounded bg-white/[0.04]" /></div>}
          {error && <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>}

          {trace && shyft && (
            <div className="space-y-6">
              <div>
                <div className={`text-xs font-semibold uppercase tracking-[0.2em] ${shyftTypeColor[shyft.severity ?? shyft.shyft_type] ?? 'text-slate-400'}`}>
                  {formatShyftLabel(shyft.severity ?? shyft.shyft_type)} · {shyft.league_name}
                </div>
                <h3 className="mt-1 text-3xl font-semibold text-ink">{shyft.player_name}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
                  {shyft.player_id != null ? (
                    <>
                      <button
                        type="button"
                        onClick={() => { navigate(`/players/${shyft.player_id}`, { state: { returnTo: window.location.pathname + window.location.search, fromFeed: true } }); onClose(); }}
                        className="transition hover:text-ink"
                      >
                        Player context
                      </button>
                      <span>•</span>
                    </>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => { navigate(`/teams/${shyft.team_id}`); onClose(); }}
                    className="transition hover:text-ink"
                  >
                    {shyft.team_name}
                  </button>
                  <span>•</span>
                  <span>{getMetricLabel(shyft)}</span>
                </div>
                {shyft.event_date && <p className="mt-1 text-xs text-muted/70">{formatEventDate(shyft.event_date)}</p>}
              </div>

              <div className="grid grid-cols-3 gap-3 rounded-[26px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Actual</div>
                  <div className={`mt-1 text-2xl font-bold tabular-nums ${shyft.trend_direction === 'up' ? 'text-success' : shyft.trend_direction === 'down' ? 'text-danger' : 'text-ink'}`}>{formatNumber(shyft.current_value)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Baseline</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-muted">{formatNumber(shyft.baseline_value)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Score</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-[#ffd8bd]">{shyft.shyft_score.toFixed(1)}/10</div>
                </div>
              </div>

              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                <div className="eyebrow mb-3">Why This Is a Shyft</div>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {[
                    ['Actual', formatNumber(shyft.debug_trace?.actual ?? shyft.current_value)],
                    ['Baseline', formatNumber(shyft.debug_trace?.baseline ?? shyft.baseline_value)],
                    ['Delta', formatSigned(shyft.debug_trace?.delta ?? shyft.current_value - shyft.baseline_value)],
                    ['Z-score', formatSigned(shyft.debug_trace?.z_score ?? shyft.z_score)],
                    ['Sample', String(shyft.debug_trace?.sample_size ?? trace.baseline_samples.length)],
                    ['Score', `${shyft.shyft_score.toFixed(1)}/10`],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded-2xl border border-white/[0.06] bg-white/[0.025] px-3 py-3">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-muted">{label}</div>
                      <div className="mt-1 text-lg font-semibold tabular-nums text-ink">{value}</div>
                    </div>
                  ))}
                </div>

                {shyft.movement_pct !== null ? (
                  <p className="mt-3 text-xs text-muted">
                    Percent movement: <span className="font-semibold text-[#d9e3f1]">{shyft.movement_pct >= 0 ? '+' : ''}{Math.round(shyft.movement_pct)}%</span>
                  </p>
                ) : null}

                {shyft.debug_trace ? (
                  <>
                    <div className="mt-4 grid gap-2 sm:grid-cols-2">
                      {Object.entries(shyft.debug_trace.conditions).map(([key, passed]) => (
                        <div key={key} className="flex items-center justify-between rounded-2xl border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-sm">
                          <span className="text-muted">{gateLabels[key] ?? key.replace(/_/g, ' ')}</span>
                          <span className={passed ? 'text-success' : 'text-danger'}>{passed ? 'Passed' : 'Failed'}</span>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 rounded-2xl border border-white/[0.06] bg-white/[0.02] px-3 py-3">
                      <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Thresholds Used</div>
                      <div className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted">
                        {Object.entries(shyft.debug_trace.thresholds).map(([key, value]) => (
                          <div key={key} className="flex justify-between gap-3">
                            <span>{key.replace(/_/g, ' ')}</span>
                            <span className="font-mono text-[#d9e3f1]">{formatThresholdValue(value)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : null}

                {shyft.score_explanation ? <p className="mt-3 text-xs leading-5 text-muted">{shyft.score_explanation}</p> : null}
              </div>

              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                <div className="eyebrow mb-2">What This Means</div>
                <p className="text-sm leading-relaxed text-[#d9e3f1]">{shyft.explanation}</p>
                {shyft.classification_reason ? <p className="mt-3 text-xs leading-5 text-muted">{shyft.classification_reason}</p> : null}
              </div>

              {trace.baseline_samples.length > 0 && (
                <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                  <div className="eyebrow mb-2">Recent History</div>
                  <div className="space-y-2">
                    {trace.baseline_samples.slice(-4).map((sample) => (
                      <div key={sample.stat_id} className="flex items-center justify-between text-sm">
                        <span className="text-muted">{formatEventDate(sample.game_date)}</span>
                        <span className="font-mono text-[#d9e3f1]">{sample.value.toFixed(1)}</span>
                      </div>
                    ))}
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
