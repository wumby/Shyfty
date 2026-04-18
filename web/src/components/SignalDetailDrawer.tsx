import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import type { SignalTrace } from '../types';
import { formatEventDate, formatSignalLabel, getMetricLabel } from '../lib/signalFormat';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import { CommentsPanel } from './CommentsPanel';

interface Props {
  signalId: number;
  onClose: () => void;
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
  const [showAllComments, setShowAllComments] = useState(false);
  const drawerRef = useRef<HTMLDivElement>(null);
  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);
  const toggleFavorite = useSignalStore((s) => s.toggleFavorite);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    setError(null);
    setTrace(null);
    api
      .getSignal(signalId)
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

  async function handleFavoriteToggle() {
    if (!currentUser) { openAuth('signin'); return; }
    if (!trace) return;
    await toggleFavorite(signalId);
    setTrace((prev) =>
      prev ? { ...prev, signal: { ...prev.signal, is_favorited: !prev.signal.is_favorited } } : prev,
    );
  }

  const signal = trace?.signal;

  return createPortal(
    <>
      <div className="fixed inset-0 z-[70] bg-black/45 backdrop-blur-[6px]" onClick={onClose} />

      <div
        ref={drawerRef}
        className="fixed bottom-3 right-3 top-3 z-[80] flex w-[calc(100%-1.5rem)] max-w-[520px] flex-col overflow-hidden rounded-[28px] border border-borderStrong bg-[#07111f]/95 shadow-2xl backdrop-blur-2xl"
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="eyebrow">Signal Analysis</div>
          <div className="flex items-center gap-3">
            {signal && (
              <button
                type="button"
                onClick={() => void handleFavoriteToggle()}
                title={signal.is_favorited ? 'Remove from saved' : 'Save signal'}
                className={`text-base transition ${signal.is_favorited ? 'text-amber-300' : 'text-muted/60 hover:text-amber-300'}`}
              >
                {signal.is_favorited ? '★' : '☆'}
              </button>
            )}
            <button type="button" onClick={onClose} className="text-xs text-muted transition hover:text-ink">
              Close ✕
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-5">
          {loading && <div className="animate-pulse space-y-4"><div className="h-6 w-48 rounded bg-white/[0.07]" /><div className="h-28 rounded bg-white/[0.04]" /><div className="h-48 rounded bg-white/[0.04]" /></div>}
          {error && <div className="rounded-xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">{error}</div>}

          {trace && signal && (
            <div className="space-y-6">
              <div>
                <div className={`text-xs font-semibold uppercase tracking-[0.2em] ${signalTypeColor[signal.signal_type] ?? 'text-slate-400'}`}>
                  {formatSignalLabel(signal.signal_type)} · {signal.league_name}
                </div>
                <h3 className="mt-1 text-3xl font-semibold text-ink">{signal.player_name}</h3>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
                  <button
                    type="button"
                    onClick={() => { navigate(`/players/${signal.player_id}`); onClose(); }}
                    className="transition hover:text-ink"
                  >
                    Player context
                  </button>
                  <span>•</span>
                  <button
                    type="button"
                    onClick={() => { navigate(`/teams/${signal.team_id}`); onClose(); }}
                    className="transition hover:text-ink"
                  >
                    {signal.team_name}
                  </button>
                  <span>•</span>
                  <span>{getMetricLabel(signal)}</span>
                </div>
                {signal.event_date && <p className="mt-1 text-xs text-muted/70">{formatEventDate(signal.event_date)}</p>}
              </div>

              {signal.freshness ? (
                <div className={`rounded-[22px] border px-4 py-3 ${
                  signal.freshness.state === 'stale'
                    ? 'border-danger/30 bg-danger/10'
                    : signal.freshness.state === 'delayed'
                      ? 'border-warning/30 bg-warning/10'
                      : 'border-border bg-white/[0.03]'
                }`}>
                  <div className="eyebrow mb-2">Board Trust</div>
                  <p className="text-sm text-ink">{signal.freshness.label}</p>
                  <p className="mt-1 text-xs text-muted">{signal.freshness.coverage_summary}</p>
                  {signal.freshness.delayed_data_message ? <p className="mt-2 text-xs text-muted">{signal.freshness.delayed_data_message}</p> : null}
                </div>
              ) : null}

              <div className="grid grid-cols-3 gap-3 rounded-[26px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">This Game</div>
                  <div className={`mt-1 text-2xl font-bold tabular-nums ${signal.trend_direction === 'up' ? 'text-success' : signal.trend_direction === 'down' ? 'text-danger' : 'text-ink'}`}>{signal.current_value.toFixed(1)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Baseline</div>
                  <div className="mt-1 text-2xl font-bold tabular-nums text-muted">{signal.baseline_value.toFixed(1)}</div>
                </div>
                <div className="text-center">
                  <div className="text-[10px] uppercase tracking-[0.14em] text-muted">Z-Score</div>
                  <div className={`mt-1 text-2xl font-bold tabular-nums ${Math.abs(signal.z_score) >= 2.5 ? 'text-fuchsia-300' : Math.abs(signal.z_score) >= 1.5 ? 'text-warning' : 'text-ink'}`}>{signal.z_score > 0 ? '+' : ''}{signal.z_score.toFixed(2)}</div>
                </div>
              </div>

              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                <div className="eyebrow mb-2">What This Means</div>
                <p className="text-sm leading-relaxed text-[#d9e3f1]">{signal.explanation}</p>
                {signal.classification_reason ? <p className="mt-3 text-[11px] uppercase tracking-[0.14em] text-muted">{signal.classification_reason}</p> : null}
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

              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <div className="eyebrow">Discussion</div>
                    <p className="mt-1 text-xs text-muted">Recent comments surface directly in detail before users open the full thread.</p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowAllComments((value) => !value)}
                    className="rounded-full border border-border px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-muted transition hover:text-ink"
                  >
                    {showAllComments ? 'Hide Thread' : 'Open Thread'}
                  </button>
                </div>
                {showAllComments ? (
                  <CommentsPanel signalId={signal.id} />
                ) : trace.discussion_preview.length > 0 ? (
                  <div className="space-y-2">
                    {trace.discussion_preview.map((comment) => (
                      <div key={comment.id} className="rounded-2xl border border-border bg-white/[0.02] px-3 py-3">
                        <div className="text-[11px] font-semibold text-[#d9e3f1]">{comment.user_email.split('@')[0]}</div>
                        <p className="mt-1 text-sm text-muted">{comment.body}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted">No discussion yet.</p>
                )}
              </div>

              {trace.related_signals.length > 0 && (
                <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-3">
                  <div className="eyebrow mb-3">Related Signals</div>
                  <div className="space-y-2">
                    {trace.related_signals.map((related) => (
                      <div
                        key={related.id}
                        className="rounded-2xl border border-border bg-white/[0.02] px-3 py-3"
                      >
                        <div className="text-[11px] uppercase tracking-[0.16em] text-muted">{formatSignalLabel(related.signal_type)}</div>
                        <div className="mt-1 text-sm font-semibold text-ink">{related.player_name}</div>
                        <div className="mt-1 text-xs text-muted">{related.explanation}</div>
                        <button
                          type="button"
                          onClick={() => {
                            setLoading(true);
                            api.getSignal(related.id).then(setTrace).finally(() => setLoading(false));
                          }}
                          className="mt-2 text-[10px] uppercase tracking-[0.14em] text-[#ffd8bd]"
                        >
                          Open signal
                        </button>
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
