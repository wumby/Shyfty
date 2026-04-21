import { NavLink, useLocation } from 'react-router-dom';

import { AuthPanel } from './AuthPanel';

const navItems = [
  { to: '/', label: 'Feed' },
  { to: '/players', label: 'Players' },
  { to: '/teams', label: 'Teams' },
  { to: '/profile', label: 'Profile' },
];

export function TopHeader() {
  const location = useLocation();
  const currentItem = navItems.find((item) =>
    item.to === '/'
      ? location.pathname === '/'
      : location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
  );

  return (
    <header className="panel-surface hero-grid relative z-20 overflow-visible px-4 py-4 sm:px-5">
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="eyebrow flex items-center gap-2">
              <span className="accent-dot" />
              Signal intelligence
            </div>
            <div className="mt-1 text-[11px] font-semibold uppercase tracking-[0.38em] text-[#ffd8bd]">Shyfty</div>
            <div className="mt-2 text-sm text-muted">
              {currentItem ? `${currentItem.label} workspace` : 'Signal workspace'}
            </div>
          </div>
          <div className="flex-shrink-0">
            <AuthPanel />
          </div>
        </div>

        <nav className="flex flex-wrap items-center gap-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `rounded-[20px] border px-3.5 py-2 text-sm font-semibold transition ${
                  isActive
                    ? 'border-accent/50 bg-accentSoft text-[#fff0e1] shadow-[0_0_0_1px_rgba(249,115,22,0.15)]'
                    : 'border-transparent bg-white/[0.02] text-muted hover:border-border hover:bg-white/[0.04] hover:text-ink'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  );
}
