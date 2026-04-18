interface EmptyStateProps {
  title: string;
  copy: string;
}

export function EmptyState({ title, copy }: EmptyStateProps) {
  return (
    <div className="flex min-h-[180px] items-center justify-center px-6 py-10 text-center">
      <div className="panel-surface max-w-md px-8 py-10">
        <div className="eyebrow">Live board needs input</div>
        <div className="mt-3 text-2xl font-semibold text-ink">{title}</div>
        <p className="mt-2 text-sm leading-6 text-muted">{copy}</p>
      </div>
    </div>
  );
}
