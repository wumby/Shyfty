import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title: string;
  description: string;
  aside?: ReactNode;
  icon?: ReactNode;
}

export function SectionHeader({ title, description, aside, icon }: SectionHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <div className="flex items-center gap-3">
          {icon ? (
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-border bg-white/[0.03] text-[#ffd8bd]">
              {icon}
            </div>
          ) : null}
          <h2 className="text-xl font-semibold text-ink">{title}</h2>
        </div>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}
