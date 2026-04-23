import type { Signal } from '../types';
import { formatEventDate, formatSignalSummary, getMetricLabel, getSignalDirection, normalizeExpectedCopy } from '../lib/signalFormat';

interface LastGameSignalCardProps {
  signals: Signal[];
  onOpenDetail?: (signalId: number) => void;
}

function getSignalPriority(signal: Signal): number {
  if (typeof signal.importance === 'number') return signal.importance;
  return Math.abs(signal.z_score);
}

function formatStatValue(signal: Signal, value: number): string {
  if (signal.metric_name === 'usage_rate') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    const rounded = Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1);
    return `${rounded}%`;
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function getOpponentLabel(signal: Signal): string | null {
  if (!signal.opponent) return null;
  const cleaned = signal.opponent.trim();
  if (!cleaned) return null;
  const parts = cleaned.split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : cleaned;
}

function getContextRow(signal: Signal): string {
  const parts: string[] = [];
  const opponent = getOpponentLabel(signal);
  const homeAway = signal.home_away === 'Away' || signal.home_away === '@' ? '@' : 'vs';
  if (opponent) parts.push(`${homeAway} ${opponent}`);
  if (signal.event_date) parts.push(formatEventDate(signal.event_date));
  return parts.join(' • ');
}

export function LastGameSignalCard({ signals, onOpenDetail }: LastGameSignalCardProps) {
  if (!signals[0]) return null;

  const sorted = [...signals].sort(
    (a, b) => getSignalPriority(b) - getSignalPriority(a),
  );
  const primarySignal = sorted[0]!;

  const primaryDirection = getSignalDirection(primarySignal);
  const isPositive = primaryDirection === 'positive';
  const isNegative = primaryDirection === 'negative';

  const borderTone = isPositive
    ? 'border-success/30 hover:border-success/55'
    : isNegative
      ? 'border-danger/30 hover:border-danger/55'
      : 'hover:border-borderStrong';

  const contextRow = getContextRow(primarySignal);
  const headline = normalizeExpectedCopy(formatSignalSummary(primarySignal));

  const result = primarySignal.game_result;
  const score = primarySignal.final_score?.replace(/\s*-\s*/g, '–') ?? null;
  const resultTone =
    result === 'W'
      ? 'bg-success/10 text-success'
      : result === 'L'
        ? 'bg-danger/10 text-danger'
        : 'bg-white/[0.05] text-muted';

  return (
    <article
      onClick={() => onOpenDetail?.(primarySignal.id)}
      className={`panel-surface cursor-pointer select-none px-5 py-5 transition-all duration-200 hover:-translate-y-0.5 sm:px-6 sm:py-6 ${borderTone}`}
    >
      {/* Player + result */}
      <div className="flex items-start justify-between gap-3">
        <span className="text-[20px] font-bold leading-tight text-ink sm:text-[22px]">
          {primarySignal.player_name}
        </span>
        {result ? (
          <span className={`shrink-0 rounded-lg px-2.5 py-1 text-[12px] font-bold ${resultTone}`}>
            {result}{score ? ` ${score}` : ''}
          </span>
        ) : null}
      </div>

      {/* Context */}
      {contextRow ? (
        <p className="mt-1 text-[12px] text-muted">{contextRow}</p>
      ) : null}
      <p className="mt-3 max-w-2xl text-[14px] font-medium leading-5 text-ink/88">
        {headline}
      </p>

      {/* Divider */}
      <div className="my-4 border-t border-white/[0.06]" />

      {/* Stat rows: value left, metric label right */}
      <div className="space-y-3">
        {sorted.map((signal) => {
          const dir = getSignalDirection(signal);
          const tone = dir === 'positive' ? 'text-success' : dir === 'negative' ? 'text-danger' : 'text-ink';
          const arrowChar = dir === 'positive' ? '↑' : dir === 'negative' ? '↓' : '→';
          const delta = signal.current_value - signal.baseline_value;

          return (
            <div key={signal.id} className="flex items-start gap-3">
              <div className="flex w-32 shrink-0 items-baseline gap-1.5 sm:w-36">
                <span className={`w-16 text-right text-[22px] font-bold tabular-nums leading-none ${tone}`}>
                  {formatStatValue(signal, signal.current_value)}
                </span>
                <span className={`text-[13px] leading-none ${tone}`} aria-hidden="true">
                  {arrowChar}
                </span>
                <span className="text-[11px] text-muted/50">
                  exp {formatStatValue(signal, signal.baseline_value)}
                </span>
              </div>
              <div className="min-w-0">
                <div className="text-[13px] font-medium text-ink/80">{getMetricLabel(signal)}</div>
                <div className={`mt-0.5 text-[11px] ${tone}`}>
                  {delta >= 0 ? '+' : ''}{formatStatValue(signal, delta)} vs expected
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
