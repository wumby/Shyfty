import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface BreadcrumbItem {
  label: string;
  to?: string;
}

interface PageIntroProps {
  eyebrow?: string;
  title: string;
  description: string;
  breadcrumbs?: BreadcrumbItem[];
  aside?: ReactNode;
}

export function PageIntro({ eyebrow, title, description, breadcrumbs, aside }: PageIntroProps) {
  return (
    <section className="panel-surface px-5 py-5 sm:px-6">
      {breadcrumbs?.length ? (
        <nav className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
          {breadcrumbs.map((item, index) => (
            <div key={`${item.label}-${index}`} className="flex items-center gap-2">
              {item.to ? (
                <Link to={item.to} className="transition hover:text-ink">
                  {item.label}
                </Link>
              ) : (
                <span className="text-ink">{item.label}</span>
              )}
              {index < breadcrumbs.length - 1 ? <span className="text-white/20">/</span> : null}
            </div>
          ))}
        </nav>
      ) : null}

      <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          {eyebrow ? <div className="eyebrow">{eyebrow}</div> : null}
          <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">{title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-muted sm:text-[15px]">{description}</p>
        </div>
        {aside ? <div className="shrink-0">{aside}</div> : null}
      </div>
    </section>
  );
}
