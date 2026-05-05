import type { ShyftFilters, SortMode } from '../types';

interface FilterDrawerProps {
  open: boolean;
  filters: ShyftFilters;
  onChange: (filters: ShyftFilters) => void;
  onClose: () => void;
}

const leagues = [
  { label: 'All', value: undefined },
  { label: 'NBA', value: 'NBA' },
  { label: 'NFL', value: 'NFL' },
];

const severities = [
  { label: 'All', value: undefined },
  { label: 'Outlier', value: 'OUTLIER' },
  { label: 'Swing', value: 'SWING' },
  { label: 'Shift', value: 'SHIFT' },
];

const sorts: Array<{ label: string; value: SortMode }> = [
  { label: 'Newest', value: 'newest' },
  { label: 'Shyft score', value: 'most_important' },
  { label: 'Biggest deviation', value: 'biggest_deviation' },
];

function FilterOption({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center justify-between rounded-[14px] px-3 py-2.5 text-left text-sm font-semibold transition ${
        active
          ? 'bg-accentSoft text-[#ffd8bd] ring-1 ring-accent/35'
          : 'bg-white/[0.025] text-muted hover:bg-white/[0.05] hover:text-ink'
      }`}
    >
      {label}
      {active ? <span className="h-2 w-2 rounded-full bg-accent" /> : null}
    </button>
  );
}

export function FilterDrawer({ open, filters, onChange, onClose }: FilterDrawerProps) {
  function updateFilter(next: ShyftFilters) {
    onChange({
      league: next.league,
      shyft_type: next.shyft_type,
      sort: next.sort ?? 'newest',
      feed: 'all',
    });
  }

  function resetFilters() {
    const next = { sort: 'newest' as SortMode, feed: 'all' as const };
    onChange(next);
  }

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-[35] bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={onClose}
        />
      )}
      <aside
        className={`fixed bottom-0 left-0 top-0 z-[41] w-[min(292px,85vw)] overflow-hidden transition-all duration-300 ease-out lg:sticky lg:top-[88px] lg:bottom-auto lg:left-auto lg:z-auto lg:h-[calc(100vh-7rem)] lg:shrink-0 ${
          open ? 'translate-x-0 lg:w-[292px] lg:opacity-100' : '-translate-x-full lg:w-0 lg:translate-x-0 lg:opacity-0'
        }`}
        aria-hidden={!open}
      >
      <div className={`flex h-full min-h-0 flex-col overflow-hidden rounded-[24px] border border-white/[0.08] bg-[#07111f]/70 shadow-soft backdrop-blur-xl transition-transform duration-300 ${open ? 'translate-x-0' : 'lg:-translate-x-6'}`}>
        <div className="flex items-center justify-between gap-3 border-b border-white/[0.07] px-4 py-4">
          <div>
            <div className="text-lg font-bold text-ink">Filters</div>
            <div className="mt-0.5 text-xs text-muted">Refine the feed.</div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={resetFilters}
              className="rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-xs font-bold text-muted transition hover:border-borderStrong hover:text-ink"
            >
              Reset
            </button>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full border border-sky-300/30 bg-sky-400/10 px-3 py-1.5 text-xs font-bold text-sky-200 transition hover:border-sky-300/50 hover:bg-sky-400/15 hover:text-sky-100"
            >
              Hide
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-6 overflow-y-auto px-4 py-5">
          <section>
            <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-muted">League</div>
            <div className="space-y-2">
              {leagues.map((option) => (
                <FilterOption
                  key={option.label}
                  label={option.label}
                  active={filters.league === option.value || (!filters.league && !option.value)}
                  onClick={() => updateFilter({ ...filters, league: option.value })}
                />
              ))}
            </div>
          </section>

          <section>
            <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-muted">Severity</div>
            <div className="space-y-2">
              {severities.map((option) => (
                <FilterOption
                  key={option.label}
                  label={option.label}
                  active={filters.shyft_type === option.value || (!filters.shyft_type && !option.value)}
                  onClick={() => updateFilter({ ...filters, shyft_type: option.value })}
                />
              ))}
            </div>
          </section>

          <section>
            <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-muted">Sort</div>
            <div className="space-y-2">
              {sorts.map((option) => (
                <FilterOption
                  key={option.value}
                  label={option.label}
                  active={(filters.sort ?? 'newest') === option.value}
                  onClick={() => updateFilter({ ...filters, sort: option.value })}
                />
              ))}
            </div>
          </section>
        </div>

      </div>
    </aside>
    </>
  );
}
