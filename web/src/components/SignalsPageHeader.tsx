interface SignalsPageHeaderProps {
  leagueLabel: string;
  typeLabel: string;
  countLabel: string;
}

export function SignalsPageHeader({ leagueLabel, typeLabel, countLabel }: SignalsPageHeaderProps) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-1">
      <div>
        <div className="eyebrow">Live Board</div>
        <h1 className="mt-0.5 text-[16px] font-semibold leading-tight text-ink sm:text-[18px]">
          Read the board.
        </h1>
      </div>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[10px] uppercase tracking-[0.18em] text-muted">
        <span>{leagueLabel}</span>
        <span className="text-white/10">/</span>
        <span>{typeLabel}</span>
        <span className="text-white/10">/</span>
        <span className="text-accent/80">{countLabel}</span>
      </div>
    </div>
  );
}
