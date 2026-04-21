import type { Signal } from '../types';
import { formatEventDate, getMetricLabel, getSignalDirection, normalizeExpectedCopy } from '../lib/signalFormat';

interface LastGameSignalCardProps {
  signals: Signal[];
  onOpenDetail?: (signalId: number) => void;
}

function formatStatValue(signal: Signal, value: number): string {
  if (signal.metric_name === 'usage_rate') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    const rounded = Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1);
    return `${rounded}%`;
  }

  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function getDirectionArrow(signal: Signal): string {
  const direction = getSignalDirection(signal);
  if (direction === 'positive') return '↑';
  if (direction === 'negative') return '↓';
  return '→';
}

function getOpponentLabel(signal: Signal): string | null {
  if (!signal.opponent) return null;
  const cleaned = signal.opponent.trim();
  if (!cleaned) return null;

  const parts = cleaned.split(/\s+/);
  return parts.length > 1 ? parts[parts.length - 1] : cleaned;
}

function getResultLabel(signal: Signal): string | null {
  if (!signal.game_result) return null;
  if (signal.game_result === 'W') return 'W';
  if (signal.game_result === 'L') return 'L';
  return signal.game_result;
}

function formatFinalScore(score: string | null | undefined): string | null {
  if (!score) return null;
  return score.replace(/\s*-\s*/g, '–');
}

function getContextRow(signal: Signal): string {
  const parts: string[] = [];
  const opponent = getOpponentLabel(signal);
  const homeAway = signal.home_away === 'Away' || signal.home_away === '@' ? '@' : 'vs';

  if (opponent) {
    parts.push(`${homeAway} ${opponent}`);
  }

  const resultLabel = getResultLabel(signal);
  if (resultLabel) {
    parts.push(formatFinalScore(signal.final_score) ? `${resultLabel} ${formatFinalScore(signal.final_score)}` : resultLabel);
  } else if (signal.final_score) {
    parts.push(formatFinalScore(signal.final_score) ?? signal.final_score);
  }

  if (signal.event_date) {
    parts.push(formatEventDate(signal.event_date));
  }

  return parts.join(' • ');
}

function getBadge(signal: Signal): { label: string; tone: string } | null {
  if (signal.signal_type === 'OUTLIER') {
    return {
      label: 'Outlier',
      tone: 'border border-fuchsia-500/20 bg-fuchsia-500/10 text-fuchsia-300',
    };
  }

  return null;
}

function getExplanation(signal: Signal): string {
  const direction = getSignalDirection(signal);
  const source = normalizeExpectedCopy(signal.explanation || signal.narrative_summary || '').toLowerCase();

  if (source.includes('far below') || source.includes('well below')) return 'Far below normal';
  if (source.includes('below')) return 'Below normal';
  if (source.includes('far above') || source.includes('well above') || source.includes('outlier')) return 'Well above typical';
  if (source.includes('above')) return 'Above typical';
  if (source.includes('shift')) return direction === 'negative' ? 'Lighter role than usual' : 'Bigger role than usual';

  if (direction === 'positive') return 'Well above typical';
  if (direction === 'negative') return 'Far below normal';
  return 'Near normal';
}

function getPrimaryBadge(signals: Signal[]): { label: string; tone: string } | null {
  const outlier = signals.find((signal) => signal.signal_type === 'OUTLIER');
  if (outlier) return getBadge(outlier);

  return null;
}

export function LastGameSignalCard({ signals, onOpenDetail }: LastGameSignalCardProps) {
  const [primarySignal, ...otherSignals] = signals;
  if (!primarySignal) return null;

  const badge = getPrimaryBadge(signals);
  const orderedSignals = [primarySignal, ...otherSignals].sort(
    (left, right) => Math.abs(right.current_value - right.baseline_value) - Math.abs(left.current_value - left.baseline_value),
  );
  const contextRow = getContextRow(primarySignal);
  const seenExplanations = new Set<string>();

  return (
    <article className="panel-surface px-4 py-3.5 sm:px-5 sm:py-4">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          {badge ? (
            <div className="mb-1.5">
              <span className={`inline-flex rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] ${badge.tone}`}>
                {badge.label}
              </span>
            </div>
          ) : null}

          <div className="text-[25px] font-semibold leading-none text-ink sm:text-[28px]">{primarySignal.player_name}</div>
          {contextRow ? <div className="mt-1 text-sm font-medium text-muted">{contextRow}</div> : null}
        </div>

        {onOpenDetail ? (
          <button
            type="button"
            onClick={() => onOpenDetail(primarySignal.id)}
            className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Details
          </button>
        ) : null}
      </div>

      <div className="mt-3 space-y-1.5">
        {orderedSignals.map((signal) => {
          const direction = getSignalDirection(signal);
          const valueTone =
            direction === 'positive'
              ? 'text-success'
              : direction === 'negative'
                ? 'text-danger'
                : 'text-ink';
          const explanation = getExplanation(signal);
          const showExplanation = explanation !== 'Near normal' && !seenExplanations.has(explanation);
          if (showExplanation) seenExplanations.add(explanation);

          return (
            <div key={signal.id} className="rounded-[14px] bg-white/[0.03] px-3 py-2">
              <div className="min-w-0">
                <div className="flex min-w-0 items-baseline gap-1.5">
                  <span className={`shrink-0 text-[21px] font-semibold leading-none tracking-tight tabular-nums sm:text-[23px] ${valueTone}`}>
                    {formatStatValue(signal, signal.current_value)}
                  </span>
                  <span aria-hidden="true" className={`shrink-0 text-[15px] leading-none ${valueTone}`}>{getDirectionArrow(signal)}</span>
                  <span className="min-w-0 truncate text-[14px] font-medium leading-tight text-ink sm:text-[15px]">
                    {getMetricLabel(signal)}
                  </span>
                  <span className="shrink-0 text-[12px] font-medium tracking-normal text-muted/75">
                    (vs {formatStatValue(signal, signal.baseline_value)})
                  </span>
                </div>
                {showExplanation ? (
                  <p className="mt-0.5 text-[12px] leading-4.5 text-muted/70">
                    — {explanation}
                  </p>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
