import { useEffect } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

import { SideNav } from './SideNav';
import { TopHeader } from './TopHeader';
import { useAuthStore } from '../store/useAuthStore';

export function AppShell() {
  const refreshSession = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  return (
    <div className="min-h-screen px-3 py-3 sm:px-4 sm:py-4 lg:px-6 lg:py-5">
      <div className="mx-auto max-w-[1520px]">
        <div className="app-frame px-3 py-3 sm:px-4 sm:py-4">
          <TopHeader />
          <div className="mt-3 grid min-h-[calc(100vh-12rem)] gap-3 lg:grid-cols-[164px,minmax(0,1fr)]">
            <aside className="hidden lg:block">
              <SideNav />
            </aside>

            <main className="relative z-0 min-w-0 rounded-[28px] border border-border bg-[#071120]/55 p-2.5 sm:p-3">
              <div className="lg:hidden px-2 pb-3">
                <nav className="flex flex-wrap items-center gap-2">
                  {[
                    { to: '/', label: 'Signals' },
                    { to: '/players', label: 'Players' },
                    { to: '/teams', label: 'Teams' },
                    { to: '/profile', label: 'Profile' },
                  ].map((item) => (
                    <NavLink
                      key={item.to}
                      to={item.to}
                      className={({ isActive }) =>
                        `pill-button ${isActive ? 'pill-button-active' : ''}`
                      }
                    >
                      {item.label}
                    </NavLink>
                  ))}
                </nav>
              </div>
              <Outlet />
            </main>
          </div>
        </div>
      </div>
    </div>
  );
}
