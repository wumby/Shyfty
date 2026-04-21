import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title: string;
  description: string;
  aside?: ReactNode;
}

export function SectionHeader({ title, description, aside }: SectionHeaderProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
      <div className="min-w-0">
        <h2 className="text-xl font-semibold text-ink">{title}</h2>
        <p className="mt-1 text-sm text-muted">{description}</p>
      </div>
      {aside ? <div className="shrink-0">{aside}</div> : null}
    </div>
  );
}
