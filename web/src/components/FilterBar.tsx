import type { SignalFilters } from '../types';

interface FilterBarProps {
  filters: SignalFilters;
  onChange: (filters: SignalFilters) => void;
}

const leagues = ['ALL', 'NBA', 'NFL'];
const types = ['ALL', 'SPIKE', 'DROP', 'SHIFT', 'CONSISTENCY', 'OUTLIER'];

const typeTone: Record<string, string> = {
  ALL: 'text-slate-300',
  SPIKE: 'text-green-400',
  DROP: 'text-red-400',
  SHIFT: 'text-amber-400',
  CONSISTENCY: 'text-blue-400',
  OUTLIER: 'text-purple-400',
};

export function FilterBar({ filters, onChange }: FilterBarProps) {
  return (
    <div className="panel-surface px-4 py-4">
      <div className="space-y-4">
        <div>
          <div className="eyebrow mb-2">League</div>
          <div className="flex flex-col gap-1">
            {leagues.map((league) => (
              <button
                key={league}
                type="button"
                className={`flex items-center justify-between rounded-[18px] border px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                  (filters.league ?? 'ALL') === league
                    ? 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                    : 'border-transparent text-muted hover:border-border hover:bg-white/[0.03] hover:text-ink'
                }`}
                onClick={() => onChange({ ...filters, league: league === 'ALL' ? undefined : league })}
              >
                <span>{league}</span>
                {(filters.league ?? 'ALL') === league ? <span className="accent-dot h-1.5 w-1.5" /> : null}
              </button>
            ))}
          </div>
        </div>
        <div>
          <div className="eyebrow mb-2">Signal Type</div>
          <div className="flex flex-col gap-1">
            {types.map((signalType) => (
              <button
                key={signalType}
                type="button"
                className={`flex items-center justify-between rounded-[18px] border px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                  (filters.signal_type ?? 'ALL') === signalType
                    ? 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                    : 'border-transparent text-muted hover:border-border hover:bg-white/[0.03] hover:text-ink'
                }`}
                onClick={() =>
                  onChange({ ...filters, signal_type: signalType === 'ALL' ? undefined : signalType })
                }
              >
                <span className={(filters.signal_type ?? 'ALL') === signalType ? 'text-[#ffd8bd]' : typeTone[signalType]}>{signalType}</span>
                {(filters.signal_type ?? 'ALL') === signalType ? <span className="accent-dot h-1.5 w-1.5" /> : null}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
