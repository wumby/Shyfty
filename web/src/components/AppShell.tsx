import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

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
          <main className="relative z-0 mt-3 min-w-0 rounded-[28px] border border-border bg-[#071120]/55 p-2.5 sm:p-3">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
