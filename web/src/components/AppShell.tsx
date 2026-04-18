import { useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { AuthPanel } from './AuthPanel';
import { useAuthStore } from '../store/useAuthStore';

const navItems = [
  { to: '/', label: 'Signals' },
  { to: '/players', label: 'Players' },
  { to: '/teams', label: 'Teams' },
];

export function AppShell() {
  const refreshSession = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  return (
    <div className="min-h-screen px-3 py-3 sm:px-4 sm:py-4 lg:px-6 lg:py-5">
      <div className="mx-auto max-w-[1640px]">
        <div className="app-frame px-3 py-3 sm:px-4 sm:py-4">
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
                      An editorial live board for player volatility, role shifts, and fast-moving team context.
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-col gap-3 lg:items-end">
                <nav className="flex flex-wrap items-center gap-2">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `pill-button ${
                      isActive
                        ? 'pill-button-active'
                        : ''
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
                </nav>
                <AuthPanel />
              </div>
            </div>
          </header>
          <main className="relative z-0 mt-3 min-h-[calc(100vh-12rem)] rounded-[28px] border border-border bg-[#071120]/70 p-2.5 sm:p-3">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
