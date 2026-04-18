import { AuthPanel } from './AuthPanel';

export function TopHeader() {
  return (
    <header className="panel-surface hero-grid relative z-20 overflow-visible px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0">
          <div className="eyebrow flex items-center gap-2">
            <span className="accent-dot" />
            Signal intelligence
          </div>
          <div className="mt-2 flex flex-wrap items-end gap-x-4 gap-y-2">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.38em] text-[#ffd8bd]">Shyfty</div>
              <div className="mt-1 max-w-xl text-sm text-muted">
                Track player volatility, role shifts, and fast-moving team context from one live board.
              </div>
            </div>
          </div>
        </div>
        <div className="flex flex-col gap-3 lg:items-end">
          <AuthPanel />
        </div>
      </div>
    </header>
  );
}
