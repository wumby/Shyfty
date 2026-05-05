import type { ShyftFilters } from '../types';

interface ActiveFilterChipsProps {
  filters: ShyftFilters;
  onRemove: (key: 'league' | 'shyft_type' | 'sort') => void;
}

const severityLabels: Record<string, string> = {
  OUTLIER: 'Outliers',
  SWING: 'Swings',
  SHIFT: 'Shifts',
};

const sortLabels: Record<string, string> = {
  newest: 'Newest',
  most_important: 'Shyft score',
  biggest_deviation: 'Biggest deviation',
};

export function ActiveFilterChips({ filters, onRemove }: ActiveFilterChipsProps) {
  const chips = [
    filters.league ? { key: 'league' as const, label: filters.league } : null,
    filters.shyft_type ? { key: 'shyft_type' as const, label: severityLabels[filters.shyft_type] ?? filters.shyft_type } : null,
    filters.sort && filters.sort !== 'newest'
      ? { key: 'sort' as const, label: sortLabels[filters.sort] ?? filters.sort }
      : null,
  ].filter(Boolean) as Array<{ key: 'league' | 'shyft_type' | 'sort'; label: string }>;

  if (chips.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      {chips.map((chip) => (
        <button
          key={chip.key}
          type="button"
          onClick={() => onRemove(chip.key)}
          className="inline-flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-[#d9e3f1] transition hover:border-accent/45 hover:text-[#ffd8bd]"
        >
          {chip.label}
          <span className="text-muted" aria-hidden="true">x</span>
        </button>
      ))}
    </div>
  );
}
