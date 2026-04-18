interface SignalsPageHeaderProps {
  leagueLabel: string;
  typeLabel: string;
  countLabel: string;
}

export function SignalsPageHeader({
  leagueLabel,
  typeLabel,
  countLabel,
}: SignalsPageHeaderProps) {
  return (
    <section className="rounded-[24px] border border-border bg-white/[0.03] px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="eyebrow">Signals</div>
          <h1 className="mt-2 text-[30px] leading-[1.02] text-ink sm:text-[34px]">
            Read the board, not just the box score.
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
            Follow the sharpest movement in player form, usage, and team context without carrying the whole dashboard at once.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] uppercase tracking-[0.2em] text-muted lg:justify-end">
          <span>{leagueLabel}</span>
          <span className="text-white/10">/</span>
          <span>{typeLabel}</span>
          <span className="text-white/10">/</span>
          <span>{countLabel}</span>
        </div>
      </div>
    </section>
  );
}
