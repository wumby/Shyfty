import type { Signal } from '../types';
import { formatEventDate, formatSignalLabel, getMetricLabel, getSignalDirection } from '../lib/signalFormat';

function formatStatValue(signal: Signal, value: number): string {
  if (signal.metric_name === 'usage_rate') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    return `${normalized.toFixed(1)}%`;
  }
  const rounded = Number.isInteger(value) ? value.toString() : value.toFixed(1);
  return rounded;
}

function getDirectionCopy(signal: Signal): string {
  const direction = getSignalDirection(signal);
  if (direction === 'positive') return 'Above normal';
  if (direction === 'negative') return 'Below normal';
  return 'Near normal';
}

function getSignalTypeTone(signalType: Signal['signal_type']): string {
  switch (signalType) {
    case 'SPIKE':
      return 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300';
    case 'DROP':
      return 'border-rose-500/20 bg-rose-500/10 text-rose-300';
    case 'CONSISTENCY':
      return 'border-sky-500/20 bg-sky-500/10 text-sky-300';
    case 'OUTLIER':
      return 'border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-300';
    case 'SHIFT':
      return 'border-amber-500/20 bg-amber-500/10 text-amber-300';
    default:
      return 'border-border bg-white/[0.03] text-muted';
  }
}

export function LastGameSignalCard({
  signal,
  onOpenDetail,
}: {
  signal: Signal;
  onOpenDetail?: (signalId: number) => void;
}) {
  const direction = getSignalDirection(signal);
  const metric = getMetricLabel(signal);
  const actualValue = formatStatValue(signal, signal.current_value);
  const expectedValue = formatStatValue(signal, signal.baseline_value);
  const dateLabel = signal.event_date ? formatEventDate(signal.event_date) : 'Last game';
  const resultLabel = signal.game_result ?? 'Result unavailable';
  const resultTone =
    signal.game_result === 'W'
      ? 'text-success'
      : signal.game_result === 'L'
        ? 'text-danger'
        : 'text-muted';
  const valueTone =
    direction === 'positive'
      ? 'text-success'
      : direction === 'negative'
        ? 'text-danger'
        : 'text-ink';
  return (
    <article className="panel-surface px-4 py-4 sm:px-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="mb-2">
            <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${getSignalTypeTone(signal.signal_type)}`}>
              {formatSignalLabel(signal.signal_type)}
            </span>
          </div>
          <div className="text-2xl font-semibold text-ink">{signal.player_name}</div>
          <div className="mt-1 text-sm text-muted">{signal.team_name} · {signal.league_name}</div>
        </div>
        {onOpenDetail ? (
          <button
            type="button"
            onClick={() => onOpenDetail(signal.id)}
            className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Details
          </button>
        ) : null}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr),220px]">
        <div className="min-w-0">
          <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">Stat</div>
          <div className="mt-1 text-3xl font-semibold text-ink">{metric}</div>
          <div className={`mt-2 text-4xl font-semibold tracking-tight ${valueTone}`}>{actualValue}</div>
          <div className="mt-2 inline-flex rounded-full bg-white/[0.03] px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">
            {getDirectionCopy(signal)}
          </div>
        </div>

        <div className="grid gap-2">
          <div className="rounded-[18px] bg-white/[0.03] px-3 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Last game</div>
            <div className="mt-1 text-xl font-semibold text-ink">{actualValue}</div>
          </div>
          <div className="rounded-[18px] bg-white/[0.03] px-3 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Expected</div>
            <div className="mt-1 text-xl font-semibold text-ink">{expectedValue}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 rounded-[18px] bg-white/[0.03] px-3 py-3 text-sm">
        <div>
          <span className="text-muted">Opponent</span>
          <span className="ml-2 font-semibold text-ink">
            {signal.opponent ? `${signal.home_away ?? 'vs'} ${signal.opponent}` : 'Unavailable'}
          </span>
        </div>
        <div>
          <span className="text-muted">Result</span>
          <span className={`ml-2 font-semibold ${resultTone}`}>{resultLabel}</span>
        </div>
        {signal.final_score ? (
          <div>
            <span className="text-muted">Final</span>
            <span className="ml-2 font-semibold text-ink">{signal.final_score}</span>
          </div>
        ) : null}
        <div>
          <span className="text-muted">Date</span>
          <span className="ml-2 font-semibold text-ink">{dateLabel}</span>
        </div>
      </div>
    </article>
  );
}
