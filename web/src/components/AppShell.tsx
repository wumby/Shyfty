import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { useAuthStore } from '../store/useAuthStore';

export function AppShell() {
  const refreshSession = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  return (
    <div className="min-h-screen">
      <AppHeader />
      <div className="px-4 py-6 sm:px-6 lg:py-8">
        <main className="relative z-0 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
