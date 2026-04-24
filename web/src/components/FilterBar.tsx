import type { Player, SignalFilters } from '../types';
import { SearchInput } from './SearchInput';

interface FilterBarProps {
  filters: SignalFilters;
  players: Player[];
  onChange: (filters: SignalFilters) => void;
  compact?: boolean;
}

const leagues = ['ALL', 'NBA', 'NFL'];
const types = ['ALL', 'OUTLIER', 'SWING', 'SHIFT'];

const typeTone: Record<string, string> = {
  ALL: 'text-slate-300',
  OUTLIER: 'text-purple-400',
  SWING: 'text-amber-400',
  SHIFT: 'text-slate-300',
};

export function FilterBar({ filters, players, onChange, compact = false }: FilterBarProps) {
  const wrapperClass = compact ? 'space-y-5' : 'panel-surface space-y-5 px-4 py-4';

  return (
    <div className={wrapperClass}>
      <div>
        <div className="eyebrow mb-2">Player Search</div>
        <SearchInput
          value={filters.player ?? ''}
          players={players}
          onChange={(val) => onChange({ ...filters, player: val || undefined })}
        />
      </div>

      <div>
        <div className="eyebrow mb-2">League</div>
        <div className="flex flex-wrap gap-2">
          {leagues.map((league) => (
            <button
              key={league}
              type="button"
              className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                (filters.league ?? 'ALL') === league
                  ? 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                  : 'border-border bg-white/[0.03] text-muted hover:border-borderStrong hover:bg-white/[0.05] hover:text-ink'
              }`}
              onClick={() => onChange({ ...filters, league: league === 'ALL' ? undefined : league })}
            >
              {league}
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="eyebrow mb-2">Severity</div>
        <div className="flex flex-wrap gap-2">
          {types.map((signalType) => (
            <button
              key={signalType}
              type="button"
              className={`rounded-full border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                (filters.signal_type ?? 'ALL') === signalType
                  ? 'border-accent/40 bg-accentSoft text-[#ffd8bd]'
                  : 'border-border bg-white/[0.03] text-muted hover:border-borderStrong hover:bg-white/[0.05] hover:text-ink'
              }`}
              onClick={() =>
                onChange({ ...filters, signal_type: signalType === 'ALL' ? undefined : signalType })
              }
            >
              <span className={(filters.signal_type ?? 'ALL') === signalType ? 'text-[#ffd8bd]' : typeTone[signalType]}>{signalType}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
